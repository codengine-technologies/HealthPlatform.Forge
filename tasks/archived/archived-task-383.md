# wip-task-383.md — Les paquets NuGet d'api-mail sont à jour et le Restore ne bloque plus sur un avis de sécurité

**Repos**: api-mail
**Dependencies**: — (aucune). Débloque la CI de `develop` (rouge depuis le merge de task-371) et `/e2e` de task-370.
**Epic**: —
**Single frontend**: true
**Priorité**: **1** — tout Restore d'api-mail échoue (CI et poste) : `NU1902` / `NU1903` en erreur sur `System.Security.Cryptography.Pkcs` 10.0.0.

> **Origine.** Constat au `/merge` de task-371 (`questions/merge-task-371.md`) : avis GHSA-846f-f764-76mx (élevé) et
> GHSA-2fmv-rv2c-59x7 (modéré) publiés le 2026-10-14 sur `System.Security.Cryptography.Pkcs` 10.0.0, transitif de
> MailKit → MimeKit. Décision humaine du 2026-10-14 : en profiter pour mettre à jour l'ensemble des paquets NuGet.

## Objective

Que le Restore d'api-mail repasse (CI et poste), et que ses dépendances NuGet soient à leur dernière version stable,
sans changement de comportement.

## Definition of Done

- [ ] `System.Security.Cryptography.Pkcs` surclassé sur une version corrigée ; Restore sans `NU190x`
- [ ] Paquets nuget.org à leur dernière version stable, sauf exceptions motivées
- [ ] `packages.lock.json` régénérés et commités
- [ ] Build sans avertissement ; tests verts
- [ ] `/e2e` vert (le backend du banc est construit avec les nouvelles versions)

## Manual Test Plan

1. Lancer l'AppHost de dev : api-mail démarre, Seq reçoit les journaux.
2. Ouvrir la messagerie (weda2 ou mobile), lire un mail avec document CDA, en envoyer un.
3. Exporter une synthèse en PDF : le document se génère.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : non applicable — maintenance des dépendances
- **Hébergement HDS** : oui — corrige un avis de sécurité sur une bibliothèque cryptographique (S/MIME de MimeKit)
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : chore/task-383-mise-a-jour-nuget — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/chore/task-383-mise-a-jour-nuget

## Develop log

- **Épingle de sécurité** : `System.Security.Cryptography.Pkcs` 10.0.13, référence directe dans `mss.mail.application`
  (pas de pinning transitif centralisé dans le dépôt, même remède que SSH.NET). Nécessaire même avec MailKit 4.18.1,
  dont MimeKit 4.18.1 dépend encore de Pkcs 10.0.0.
- **45 paquets montés** (relevé `dotnet list package --outdated`, source nuget.org) : Aspire 13.6.1, ASP.NET Core /
  EF Core / Microsoft.Extensions 10.0.13, Microsoft.Extensions.Http.Resilience et ServiceDiscovery 10.11.0, MailKit
  4.18.1, AngleSharp 1.8.4, Hl7.Fhir.R4 6.6.0, Markdig 1.4.0, MessagePack 3.1.12, SemanticKernel 1.81.0,
  OpenTelemetry 1.19, Swashbuckle 10.3.0, System.IdentityModel.Tokens.Jwt 8.23.0, Testcontainers 4.16.0,
  YamlDotNet 18.1.0, Microsoft.NET.Test.Sdk 18.11.0, xunit (runner 4.0.1, v3 4.0.2), coverlet 10.1.0.
- **Non montés, motivés** :
  - **QuestPDF reste 2026.8.0** : 2026.9 n'utilise plus les polices système et **arrête** la génération quand une
    police manque (Consolas, absente sous Linux) — `MarkdownPdfRendererTests.RenderInlineEmphasisKeepsText` rouge
    (`DocumentDrawingException`). La montée demande d'embarquer une police monospace : task à part.
  - **MassTransit reste `[8.3.6]`** (version figée) : la v9 passe sous licence commerciale — décision humaine.
  - Paquets internes (`HealthPlatform.Dtos.Mss`, `HealthPlatform.Host.Sdk`, `Interop.Cda.Parser`) : montés par la
    forge à chaque changement de contrat. Préversions (`SemanticKernel.Connectors.Ollama`, `Exporter.Prometheus`,
    `Instrumentation.Process`) : aucune préversion plus récente proposée.
- **Validation (worktree)** : Restore sans erreur ; build 0 avertissement ; domain 195, infrastructure 690, api 1 231,
  application 3 642 verts. Intégration : 885 verts, 2 rouges (`Le_maintien_des_partitions…`,
  `SearchMedicalDocumentsByVectorAsync…`), verts isolés — **et rouges aussi avec les anciennes versions dans le même
  worktree** : effet de l'emplacement (dossier du worktree), pas des paquets. Avec les anciennes versions dans le
  checkout principal : 887/887. Suite rejouée dans le checkout principal après déplacement de la branche.
- Relevé du flux GitHub Packages refusé (401, jeton) : seule la source nuget.org a été interrogée.
- **Validation (checkout principal, branche déplacée)** : Restore sans erreur ; build 0 avertissement ; domain 195,
  infrastructure 690, api 1 231, application 3 642, **intégration 887/887** (16 ignorés préexistants). Les deux rouges
  du worktree tenaient à son emplacement. Commit `2d535bd4`.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché | ✅ verte | 37 verts, 0 flaky, 0 rouge | ~6 min |
| angular | api-mail touché | ✅ verte | 40 verts, 1 flaky (E2E-LIVE-001), 0 rouge, 1 quarantaine (passée) | ~6 min |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ chore/task-383-mise-a-jour-nuget (après merge de `develop`, task-374 compris)
- Backend du banc construit sur la branche (nouvelles versions). Mobile joué sur `fix/task-370-session-weda2` (merge de `develop` + correctif du test E2E-ATTACH-001) ; weda2 avec le correctif du menu « Plus d'actions » (task-370, non commité).
- Historique : 1er passage vert (avant merge de `develop`) ; 2e rouge — parité E2E-MAILBOX-001 (branche mobile antérieure à task-374) et E2E-COMPOSE-001 (défaut produit corrigé dans task-370).
- Démontage : complet (ports libres, aucun conteneur e2e résiduel)

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « temps réel — un compte rendu arrive, notifié et affiché sans rechargement » (E2E-LIVE-001)

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 2 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ⚠️ flaky | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 1 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 1 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/298 — label `awaiting-human-merge`

## Code Review Summary

**APPROVED** — 0 bloquant, 1 suggestion (QuestPDF 2026.9 dans une task dédiée).

- Règle 1b : aucun comportement d'endpoint modifié (aucun code) ; suite d'intégration complète verte (887).
- Double verrou e2e : `## E2E log` vert (mobile 37/37, angular 40/40, parité verte, 1 flaky E2E-LIVE-001).
- Merge de `develop` (task-374) : épingle Pkcs en doublon fusionnée, lock files régénérés, build et tests reverts.

## Timings

*(généré par `tools/timing/report.sh --task task-383 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /develop | en cours | — | 4 (32 s) | 3 (11 min 23 s) | — | api-mail 4B/3T |
| /e2e | ok | 14 min 18 s | — | — | — | e2e ×9 (39 min 36 s), rejeu vert après merge de develop |
| /review | ok | 42 min 13 s | 2 (18 s) | 2 (7 min 34 s) | — | api-mail 2B/2T |
| **Total cycle** | | **56 min 32 s** | **6 (51 s)** | **5 (18 min 58 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : restore ×3 (26 s)

## Merged

- 2026-10-14 — `/merge task-383 --i-tested`
- api-mail : PR #298 squashée — `ba913e42` ; CI `develop` ✅ https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/38628496806 (rouge depuis le merge de task-371, débloquée)
- Branche `chore/task-383-mise-a-jour-nuget` supprimée (distante et locale)
