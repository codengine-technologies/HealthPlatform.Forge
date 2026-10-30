# todo-task-406 — Mesurer la charge d'une boîte partagée

**Repos**: api-mail
**Dependencies**: task-404 (une base par boîte)
**Epic**: E020

> **Single repo justifié** : US de **mesure** sur le banc de charge E015 (`Api/Mail/tests/loadtest-k6`,
> `LoadTestRegistryProvisioner`). Aucun comportement produit ni écran ne change.

## Ce qui est établi

- **Bornes du pool Npgsql par base** (`Api/Mail/src/AppHost/AppHost.cs:471-500`) : 2 connexions sur
  le banc de charge (borne anti-OOM mesurée : « connexions retenues = praticiens × répliques × Max
  Pool Size »), 10 en développement, plafond de rafale derrière PgBouncer.
- **Avec la task-404**, N personnes d'une même boîte partagent **un** pool au lieu de N : le parc
  compte moins de bases, chacune plus chargée. La règle qui a fixé les bornes change de sens, sans
  avoir été mesurée.
- **Invariants connus du banc** (mémoire `project_loadtest_bench_greenmail`) : bases Postgres par
  utilisateur persistantes, limiteur 100 req / 10 s par identité, 10 connexions IMAP par utilisateur.

## Objective

Établir, mesures à l'appui, ce que coûte le travail de plusieurs personnes sur une même base, et
dire si les bornes du pool, la synchronisation et l'enrichissement tiennent, ou ce qu'il faut
changer. US de **mesure** : elle produit un verdict chiffré, pas une optimisation.

## Règles

1. **Deux profils comparés, à charge totale égale** : N personnes sur **une** boîte (adresse
   organisationnelle, boîte très déléguée) contre N personnes sur N boîtes (référence).
2. **N = 2, 5, 10.**
3. **Mesures** : p50 / p95 par route ; erreurs « pool épuisé » ; connexions Postgres retenues ;
   attente des verrous de synchronisation et d'enrichissement ; nombre d'enrichissements CDA et
   d'appels IA par message — **1**, pas N (preuve que la copie par personne a disparu).
4. **Verdict écrit** dans `Docs/audits/` : bornes à garder ou à changer. Toute modification de borne
   est une **task de suite**, pas cette US.
5. **Invariants du banc respectés** : chaque personne du profil a sa propre identité (limiteur par
   identité).

## Definition of Done

- [x] Build passes (0 errors) sur `api-mail`
- [x] Tests pass (0 failures) sur `api-mail`
- [x] `LoadTestRegistryProvisioner` provisionne N identités PSC rattachées à **une** boîte (une
      titulaire, N−1 délégataires)
- [x] Unit tests du provisionnement partagé (rôles, une seule base au registre)
- [x] Profil k6 « boîte partagée » et profil de référence, paramétrés par N
- [x] Tirs réalisés pour N = 2, 5, 10 ; mesures consignées dans `metrics/` et dans le rapport
- [x] Enrichissements CDA et appels IA comptés : 1 par message quel que soit N
- [x] Rapport `Docs/audits/boite-partagee-charge-{date}.md` : tableaux comparatifs, verdict sur les
      bornes, tasks de suite proposées s'il y a lieu
- [x] Aucune donnée de santé réelle sur le banc (données synthétiques)

## Manual Test Plan

- Monter le banc de charge (skill `loadtest-skill`), provisionner le profil partagé avec N = 5.
- Tirer les deux profils ; lire le rapport : comparaison p95 / pool lisible, verdict explicite.
- `psql -c '\l'` : une seule base pour la boîte partagée ; connexions retenues conformes au rapport.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : non applicable — banc de charge
- **Vague Ségur** : hors Ségur — mesure interne
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — données synthétiques
- **Authentification PS** : non applicable — identités synthétiques du banc
- **Habilitations** : non applicable — rôles provisionnés sur le banc
- **Interop CI-SIS** : non applicable — IHE-XDM synthétiques existants du banc
- **Tracé PGSSI-S** : traces du tir émises normalement ; volume mesuré
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — banc local sans donnée réelle
- **AIPD / impact RGPD** : inchangée

## Branches

- `api-mail` (pushed) : feat/task-406-mesurer-la-charge-d-une-boite-partagee — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-406-mesurer-la-charge-d-une-boite-partagee

## Develop log

**Repo** : `api-mail` (code de test et harnais seulement : aucun comportement produit ne change).

| Commit | Contenu |
|---|---|
| `2f936031` | `LoadTestRegistryProvisioner.ProvisionSharedBoxesAsync` ; seed `--shared-box N` (délégations et réglages de chaque délégataire dans la boîte partagée) ; k6 `SHARED_BOX=N` (boîte de la première personne du groupe, nom PSC envoyé, From = boîte ouverte) |
| `5ab830ef` | Outillage aligné sur le nommage des bases de task-404, voir ci-dessous ; identifiant de session étiqueté par la boîte ouverte (garde task-365) |

**Tests** :
- `LoadTestRegistryProvisionerTests` : 5 tests de la boîte partagée (délégations sur la base de la
  titulaire, plusieurs groupes, idempotence, groupe < 2 refusé, domaine hors banc refusé). Rouges
  avant l'implémentation (méthode absente).
- `SeedOptionsTests` : `--shared-box`.
- **Intégration** : `LoadTestBenchProvisioningIntegrationTests.ASharedBenchBox_HasOneDatabase_AndEachDelegateReachesItUnderItsOwnIdentity`,
  sur un vrai registre PostgreSQL. Une seule base pour la boîte, rôle `Delegate`, et chaque délégataire
  atteint la route de messagerie de la boîte avec son propre tenant.
- Harnais JS : `node --test lib/*.test.mjs` passe 127/127, dont `shared-box.test.mjs`.

**Campagne** (2026-10-30, détail dans `Docs/audits/boite-partagee-charge-2026-10-30.md`) :
- Tirs `mixed` de 3 min, N = 2, 5, 10, référence contre boîte partagée, banc mail sur le cluster,
  tireur local, IA tout-OpenAI. Les données brutes sont dans
  `Docs/audits/boite-partagee-charge-2026-10-30.json`.
- **Verdict** :
  - les bornes du pool Postgres tiennent (attente de connexion ≈ 0,1 ms, 0 pool épuisé) ;
  - CDA et IA comptent 1 par message quel que soit N (~124 contre N × ~122) ;
  - le coût du partage est dans les sessions et les verrous de la boîte. À 5 et 10 personnes,
    l'ouverture et l'envoi doublent, et l'attente des verrous de récupération atteint 520 s cumulées à
    N = 10.
- **Tasks de suite proposées** (non créées) :
  - `MaxSessionsPerMailbox` par personne : déjà dans task-411, désormais mesuré ;
  - lecture concurrente d'un même message.

**Outillage corrigé (règle d'or)** :
- `reset-state.sh`, `verify.sh`, `pg-statements.sh` et `pg-connections.sh` filtraient `u_9…`. Depuis
  task-404, le nom de base ne porte plus le RPPS : aucune base n'était trouvée, sans erreur.
- Les noms sont désormais recalculés depuis les identités du banc, et `reset-state.sh --users N` borne
  la purge.
- Le correctif est documenté dans le README du harnais (§ 2, état persistant).

**État du banc après la campagne** :
- AppHost arrêté, conteneurs du banc arrêtés, aucune archive CDA dans `%TEMP%`.
- Le registre `mss_registry_loadtest` est recréé : comptes 1..10 et délégations des groupes 2, 5 et 10.
- Les bases des boîtes 1..10 restent, purgées par le dernier tir.
- Le maildir du cluster n'a pas été touché.

**Passe qualité §Q** : diff de test et de harnais seulement, aucun nettoyage nécessaire.

## Sonar log

- Serveur 9.9.8.100196 (`sonar.login`), projet `healthplatform-api-mail`, branche `feat/task-406-…`.
- **Phase 1 (code neuf)**, une analyse : Quality Gate OK, **0 issue ouverte**, 0 hotspot. Le diff ne
  touche que le code de test et le harnais.
- **Phase 2 (dette existante)** : 0 itération (0 bug, 0 vulnérabilité, 0 code smell).
- Build Release et 5 suites OpenCover : domain 202, application 3 939, infrastructure 699, api 1 315,
  integration 1 080 verts et 16 ignorés.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 96,4 % | 96,4 % | 0 |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 | 0 |
| Coverage (projet) | 97,8 % | 97,8 % | 0 |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

- `client-angular` : non touché par la task (`**Repos**: api-mail`). Skip.

## Lint mobile log

- `client-mobile` : non touché par la task. Skip.

## E2E log

| Voie | Jouée | Résultat |
|---|---|---|
| mobile | jouée (api-mail touché) | ✅ 54 verts, 0 flaky, parité verte |
| angular | jouée (api-mail touché) | ✅ 65 verts, 0 flaky, parité verte |

La task ne change aucun parcours médecin : le code produit est inchangé, seuls le code de test et le
harnais bougent. Aucun scénario n'est donc ajouté. Démontage vérifié : ports libres, aucun conteneur
e2e résiduel.

Signaux pour l'humain, déjà relevés en task-407 :
- la divergence E2E-MAILBOX-002 [angular] est **à retirer** ;
- la quarantaine E2E-COMPOSE-002 [angular] (task-350) est verte.

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
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ · divergence (task-395) | ✅ |
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

**Divergences temporaires ouvertes** (1) :

- E2E-MAILBOX-002 [angular] — le code weda2 de task-378 (écran de panne à l'entrée et son test) n'est pas encore livré sur la branche weda2 ; divergence décidée par l'humain le 2026-10-25 — résorbée par task-395 — **à retirer** : le client est revenu à la version du catalogue

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/329 — `awaiting-human-merge`

## Code Review Summary

**APPROVED**. 0 point bloquant.

- **Règle 1b** : aucun comportement produit atteignable par un endpoint ne change. Le diff ne touche
  que le code de test partagé, le seed et le harnais k6. Le provisionnement partagé est prouvé de bout
  en bout sur un vrai registre par `ASharedBenchBox_HasOneDatabase_AndEachDelegateReachesItUnderItsOwnIdentity` :
  une base, rôle Delegate, chaque délégataire atteint la route de la boîte avec son tenant.
- ✅ `ProvisionSharedBoxesAsync` passe par le contrat du registre, jamais par du SQL. Le nom de base est
  celui de la titulaire. Il est idempotent et refuse un domaine hors banc.
- ✅ Les scripts de banc recalculent les noms de base depuis les identités. C'est un correctif réel :
  depuis task-404, purge et vérification ne voyaient plus rien, sans erreur.
- ⚠️ `ProvisionSharedBoxesAsync` ne revérifie pas seule que le registre est un registre de banc. Elle
  compte sur `ProvisionAsync`, toujours appelée avant elle par le seed.
- ⚠️ Le message final du seed annonce N utilisateurs même quand il a aussi écrit les réglages des
  délégataires.

## Timings

*(généré par `tools/timing/report.sh --task task-406 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 21 s | — | — | — | — |
| /develop | ok | 47 min 41 s | 1 (21 s) | — | — | api-mail 1B/0T |
| /sonar | ok | 11 min 00 s | 1 (53 s) | 5 (8 min 27 s) | 2 (55 s) | api-mail 1B/5T |
| /lint-angular | skipped | 0.5 s | — | — | — | client-angular non touché |
| /lint-mobile | skipped | 0.6 s | — | — | — | client-mobile non touché |
| /e2e | ok | 19 min 41 s | — | — | — | e2e ×5 (38 min 00 s) |
| /review | ok | 6 min 16 s | 1 (11 s) | 1 (5 min 06 s) | — | api-mail 1B/1T |
| **Total cycle** | | **1 h 25 min** | **3 (1 min 26 s)** | **6 (13 min 34 s)** | **2 (55 s)** | |
