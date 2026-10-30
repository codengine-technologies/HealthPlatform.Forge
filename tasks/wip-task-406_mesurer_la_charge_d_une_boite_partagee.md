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

## Timings

*(généré par `tools/timing/report.sh --task task-406 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 21 s | — | — | — | — |
| /develop | ok | 47 min 41 s | 1 (21 s) | — | — | api-mail 1B/0T |
| /sonar | ok | 11 min 00 s | 1 (53 s) | 5 (8 min 27 s) | 2 (55 s) | api-mail 1B/5T |
| /lint-angular | skipped | 0.5 s | — | — | — | client-angular non touché |
| /lint-mobile | skipped | 0.6 s | — | — | — | client-mobile non touché |
| **Total cycle** | | **59 min 04 s** | **2 (1 min 14 s)** | **5 (8 min 27 s)** | **2 (55 s)** | |
