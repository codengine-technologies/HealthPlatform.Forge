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

- [ ] Build passes (0 errors) sur `api-mail`
- [ ] Tests pass (0 failures) sur `api-mail`
- [ ] `LoadTestRegistryProvisioner` provisionne N identités PSC rattachées à **une** boîte (une
      titulaire, N−1 délégataires)
- [ ] Unit tests du provisionnement partagé (rôles, une seule base au registre)
- [ ] Profil k6 « boîte partagée » et profil de référence, paramétrés par N
- [ ] Tirs réalisés pour N = 2, 5, 10 ; mesures consignées dans `metrics/` et dans le rapport
- [ ] Enrichissements CDA et appels IA comptés : 1 par message quel que soit N
- [ ] Rapport `Docs/audits/boite-partagee-charge-{date}.md` : tableaux comparatifs, verdict sur les
      bornes, tasks de suite proposées s'il y a lieu
- [ ] Aucune donnée de santé réelle sur le banc (données synthétiques)

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

## Timings

*(généré par `tools/timing/report.sh --task task-406 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 21 s | — | — | — | — |
| **Total cycle** | | **21 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
