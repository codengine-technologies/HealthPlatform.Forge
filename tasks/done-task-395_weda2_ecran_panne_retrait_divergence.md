# todo-task-395.md — Livrer sur weda2 le code de task-378 (écran de panne à l'entrée) et retirer la divergence E2E-MAILBOX-002

**Repos**: client-angular, api-mail
**Dependencies**: task-378 (mergée côté api-mail et mobile)
**Epic**: E016
**Single frontend**: true
**Priorité**: **2** — tant que ce code manque, le scénario requis E2E-MAILBOX-002 est en divergence temporaire côté
weda2, et weda2 n'a pas l'écran de panne à l'entrée qu'ont api-mail et le mobile.

> **Origine.** `/e2e` de task-394 (2026-10-25) : après la synchronisation avec `develop`, la porte bloquait sur
> E2E-MAILBOX-002 « requis pour angular mais absent de sa suite ». Le code weda2 de task-378, écrit en code seul sur
> `feature/nova-mss-weda-integration` (17 fichiers modifiés et `libs/mss/src/features/mailbox-unavailable/`, d'après
> `tasks/archived/archived-task-378.md`), n'est plus dans le clone : ni dans l'arbre de travail, ni dans un stash, ni
> dans un commit. L'humain a décidé une **divergence temporaire** côté angular, résorbée par cette task.

## Objective

weda2 affiche, comme le mobile, l'écran « service indisponible » quand api-mail ne répond pas à l'entrée, avec
« Réessayer ». Le test E2E-MAILBOX-002 weda2 est livré, et la divergence est retirée du catalogue.

## Definition of Done

- [ ] Le code weda2 de task-378 est retrouvé (clone ou poste où il a été écrit), ou réécrit d'après
      `tasks/archived/archived-task-378.md`, sur la branche weda2
- [ ] E2E-MAILBOX-002 implémenté dans `Client/Angular/front/e2e/mss-e2e/specs/functional.e2e.ts` à la version du
      catalogue, et prouvé rouge par mutation
- [ ] Divergence `angular` de E2E-MAILBOX-002 retirée de `Api/Mail/e2e/scenarios.yml`
- [ ] Build et tests weda2 verts ; `/e2e` vert avec parité verte, sans divergence

## Manual Test Plan

1. weda2, api-mail arrêté : ouvrir la messagerie. L'écran dit que le service est indisponible et propose
   « Réessayer », sans l'écran « Pro Santé Connect requis » ni l'ajout d'une messagerie.
2. Relancer api-mail, puis cliquer « Réessayer » : la boîte de réception s'affiche.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur, robustesse de l'entrée dans la messagerie
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé (déjà livré par task-378 côté api-mail)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : feat/task-395-weda2-ecran-panne-retrait-divergence — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-395-weda2-ecran-panne-retrait-divergence
- `client-angular` (code-only) : la forge travaille sur la branche courante de `Client/Angular/` (`feature/nova-mss-weda-integration` au /start) — humain gère branche, commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-395 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 13 s | — | — | — | — |
| /develop | ok | 4 min 06 s | 1 (13 s) | 1 (4.5 s) | — | api-mail 1B/1T |
| /sonar | skipped | 0.8 s | — | — | — | diff = e2e/scenarios.yml seul, aucun C# changé depuis l'analyse task-419 |
| /lint-angular | skipped | 0.8 s | — | — | — | aucun code Angular écrit par la forge (arbre propre) |
| /lint-mobile | skipped | 0.6 s | — | — | — | client-mobile non touché |
| /e2e | ok | 19 min 05 s | — | — | — | e2e ×5 (37 min 31 s) |
| /review | ok | 7 min 12 s | 2 (16 s) | 2 (6 min 15 s) | — | api-mail 1B/1T, client-angular 1B/1T |
| **Total cycle** | | **30 min 40 s** | **3 (30 s)** | **3 (6 min 20 s)** | **0 (0.0 s)** | |

## Develop log

- **Repos touchés** : `api-mail` (catalogue e2e). `client-angular` : aucun changement. Le code et le test weda2 de task-378 sont déjà sur `feature/nova-mss-weda-integration` (commit `85a13925` « Task 378 », `libs/mss/src/features/mailbox-unavailable/`), retrouvés dans le clone.
- **Aucun DTO, aucun interop.**
- **Commit** : api-mail `7b42ed1c` test(e2e) : divergence `angular` d'E2E-MAILBOX-002 retirée de `Api/Mail/e2e/scenarios.yml`, l'origine mentionne la résorption.
- **E2E-MAILBOX-002 sur weda2** : le test `functional.e2e.ts:3358` déclare `scenario('E2E-MAILBOX-002', 1)`, la version du catalogue.
  - Il passe sur un banc e2e monté pour l'occasion (`run.mjs --serve-only`).
  - **Vu rouge par mutation** : `data-testid="mailbox-unavailable"` renommé dans `mss-mailbox-unavailable.component.html` → « la panne est dite comme une panne : expect(locator).toBeVisible() failed ».
  - Restauré par copie, rejoué au vert. L'arbre weda2 est propre et le banc démonté.
- **Build / tests** : api-mail build vert ; `ScenarioCatalogTests` 17/17. weda2 n'est pas modifié : son build et ses tests sont rejoués par `/review`.
- **Passe qualité (/simplify)** : rien à simplifier (une modification YAML).
- **DOD** :
  - code weda2 retrouvé ✓ ;
  - test à la version du catalogue et vu rouge ✓ ;
  - divergence retirée ✓ ;
  - `/e2e` parité sans divergence → étape `/e2e`.
- **Étape suivante** : `/sonar task-395`.

## Sonar log

- **Sonar : skip mesuré**. Le diff api-mail se limite à `e2e/scenarios.yml`, hors des sources analysées (C#). Aucun fichier C# n'a changé depuis la dernière analyse complète (`72b82aec`, task-419, 2026-11-01), identique à `develop` @ `f2732115`.
- KPIs de cette analyse, valables pour ce code : Quality Gate OK ; new coverage 96,2 % ; bugs / vulnérabilités / code smells / hotspots 0 / 0 / 0 / 0 ; coverage 97,8 % ; duplication 0,4 % ; ratings A/A/A.

## Lint log

- **/lint-angular** : skip — aucun code Angular écrit par la forge (arbre `Client/Angular/front` propre) ; le code weda2 de task-378 est déjà commité par l'humain sur `feature/nova-mss-weda-integration`.
- **/lint-mobile** : skip — `client-mobile` absent des `**Repos**`, sur `develop`, arbre propre.

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail touché (catalogue) | ✅ verte (jouée) | 57 verts, 0 flaky, 0 rouge | ~9 min |
| angular | api-mail touché (catalogue) | ✅ verte (jouée) | 68 verts, 0 flaky, 0 rouge, 1 quarantaine (passée) | ~10 min |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ branche de la task (divergence E2E-MAILBOX-002 retirée)
- Quarantaines : E2E-COMPOSE-002 [angular] (correction : task-350), passée
- Divergences ouvertes : **aucune**
- Parcours touchés sans spec e2e modifié : aucun
- Démontage : complet (ports libres, aucun conteneur e2e résiduel)

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ✅ | — |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 2 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/335 — label `awaiting-human-merge`
- `client-angular` (code-only) : aucun fichier modifié par la forge ; le code weda2 de task-378 est déjà commité sur `feature/nova-mss-weda-integration` (`85a13925`) — humain gère push TFS et PR.

## Code Review Summary

- **APPROVED** — 1 fichier (`e2e/scenarios.yml`), 0 point bloquant.
- Règle 1b : sans objet (catalogue de tests seul, aucun comportement d'endpoint changé).
- Parcours weda2 E2E-MAILBOX-002 vu rouge par mutation (`data-testid` de l'écran de panne renommé).
- Validation : api-mail 7 263 tests verts ; weda2 build + tests (12 projets) verts ; `/e2e` vert, aucune divergence ouverte.
