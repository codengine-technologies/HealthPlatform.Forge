# todo-task-115.md — Refonte Stitch composant `mail-list` (mobile)

**Repos**: client-mobile
**Dependencies**: done-task-110
**Single frontend**: true
**Epic**: E014

## Objective
Refondre **structurellement** la liste des emails `mail-list`
(`src/app/features/mail/components/mail-list/*`) pour une fidélité parfaite à sa
**référence Stitch** `mail-list`, sur la base du socle `done-task-110`.

Lignes **haute densité** (≥ 56px) : avatar expéditeur, nom en gras, sujet,
extrait, horodatage aligné à droite, pastille non-lu, chips de statut (flag, PJ,
biologie). Travail **soigné** exigé. `client-mobile` uniquement — aucun
changement fonctionnel.

## Référence Stitch
- **Réutiliser** l'écran Stitch `mail-list` (correspondance exacte).
- Étape design : `/stitch-design task-115`. Stitch = référence, pas du code.

## Definition of Done
- [ ] Build passe (`npm ci && npm run build`, 0 erreur)
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] Structure de ligne alignée sur Stitch : avatar, nom gras, sujet, extrait,
      horodatage, pastille non-lu, chips statut (flag/PJ/bio), hauteur ≥ 56px,
      séparateurs 1px
- [ ] Tokens du socle réutilisés — aucune valeur de design en dur
- [ ] `data-testid` préservés/complétés sur les lignes et actions
- [ ] Aucune régression (sélection, ouverture d'un mail, états lu/non-lu)
- [ ] Comparaison visuelle avec le screenshot Stitch consignée

## Manual Test Plan
- Lancer le mobile, ouvrir l'inbox affichant `mail-list`.
- Vérifier le rendu des lignes (densité, avatar, chips, pastille non-lu,
  horodatage) au nouveau design.
- Ouvrir un mail, marquer lu/non-lu → comportement inchangé.
- Comparer à la maquette Stitch `mail-list`.

## Conformité santé / Ségur / ANS
- **Couloir / Vague Ségur** : hors couloir / hors Ségur — restyling UI.
- **DSR / INS / Authentification / Habilitations / Interop / PGSSI-S /
  Consentement / Référentiels / HDS / RGPD** : non applicable. Ne jamais exposer
  d'INS/contenu MSSanté en clair dans l'UI.

## Branches
- `client-mobile` (pushed) : feat/task-115-refonte-stitch-mail-list — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-115-refonte-stitch-mail-list

## Stitch design log

- Project : client-mobile (id 10088502293310567548)
- Screens :
  | Component / Page | Stitch title | Screen id | Action | Screenshot |
  |---|---|---|---|---|
  | mail-list | mail-list | 09bc742258d14caabd40dc311ee04c24 | reused | (récupéré via get_screen, consigné en session) |
- ⚠ Rename needed in Stitch UI : none.
- Stitch reachable : ✓
- Intention reprise : lignes haute densité, avatar **carré arrondi** coloré,
  nom gras + pastille non-lu, sujet/extrait, chips de statut (Document médical v,
  Biologie CRITIQUE en rouge, 3 messages, À rattacher), horodatage à droite,
  accent gauche rouge sur ligne critique, réponses de fil indentées plus claires,
  séparateurs 1px.

## Develop log

- Repos touched : client-mobile (seul repo de la task)
- DTOs / Interop : aucun changement de contrat
- Périmètre : reprise **structurelle/visuelle** de la ligne `mail-list` (rendue
  par `mss-mail-header`) + conteneur `mss-mail-list`, sans toucher la logique.
  Les acquis de l'extension task-114 (valeurs biologie inline, regroupement,
  pilules) sont **préservés**. Les internes profonds de `mail-header` (API
  @Input/@Output, structure) restent du ressort de task-118.
- Implémentation (Stitch = référence, traduit en Ionic + tokens socle) :
  - `mail-header.component.scss` : réécriture **100 % token-driven** — avatar
    carré arrondi (`--app-radius-lg`), séparateur `--app-outline-variant`, fonds
    d'état (`--app-surface-container*`), typographies `--app-type-*`, accent
    critique gauche `--ion-color-tertiary`, hauteur `--app-list-row-min-height`.
  - `mail-header.component.ts/html` : libellé « Biologie CRITIQUE » quand un
    acquittement critique est en attente (`biologyChipLabel`), classe
    `mail-row--critical` (accent rouge).
  - `mail-list.component.scss` : réponses de fil indentées plus claires + état
    vide, token-driven.
- Tests : +2 specs `mail-header` (label critique, accent critique).
- Local build / test : ✓ (npm run build OK ; **135/135** tests OK, headless).
- DOD self-check :
  - Build passe ✓ ; Tests passent (135/135) ✓
  - Structure de ligne alignée (avatar carré arrondi, nom gras, sujet, extrait,
    horodatage droite, pastille non-lu, chips statut flag/PJ/bio, ≥56px,
    séparateurs 1px) ✓
  - Tokens du socle réutilisés, aucune valeur de design en dur ✓
  - data-testid préservés (mail-row-*, mail-medical-*, mail-biology-*, mail-attach-*, swipe-*) ✓
  - Aucune régression (sélection/ouverture/lu-non-lu inchangés ; tests verts) ✓
  - Comparaison visuelle screenshot Stitch : ⏸ déferré (HAG) — test humain sur l'app lancée
- Next step : /forge-simplify task-115

## Simplify log

- Repo : client-mobile (seul repo touché)
- Verdict : **skip clean** — rien à simplifier. La réécriture de
  `mail-header.scss` est token-driven sans duplication, `biologyChipLabel` est
  un getter trivial, la token-isation de `mail-list.scss` réutilise les tokens
  du socle. Aucun gain reuse/simplif/efficacité/altitude matériel.
- dtos-mss / interop-cda : non touchés (hors scope simplify).
- Next step : /lint-mobile task-115 (api-mail non touché → /sonar skip ;
  client-angular non touché → /lint-angular skip).

## Lint mobile log

- Repo : client-mobile (Working dir Client/Mobile/)
- Baseline `npm run lint` (ng lint) : **All files pass linting** — 0 erreur, 0 warning.
- Aucun fix, aucune itération, aucun commit (diff TS/HTML/SCSS ESLint-clean).
- Next step : /review task-115

## PRs
- `client-mobile` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/20 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : **APPROVED** (refonte présentation HTML/SCSS/TS, 0 blocking).
- `mail-header.component.scss` — ✅ réécriture token-driven (avatar carré, séparateurs/fonds/typo via socle, accent critique). Constantes dimensionnelles + 1 teinte rgba dérivée du tertiaire conservées (acceptable).
- `mail-header.component.ts/html` — ✅ `biologyChipLabel` (« Biologie CRITIQUE ») + classe `mail-row--critical`.
- `mail-list.component.scss` — ✅ lignes de fil indentées plus claires + état vide token-driven.
- Acquis task-114 (valeurs biologie inline, regroupement) préservés.
- Build ✓ | Tests 135/135 ✓ | Lint ✓.
- ⚠ DOD « comparaison visuelle » Stitch : déféré au test humain (HAG).

## Merged

- Date : 2026-06-24 (human-triggered `/merge task-115 --i-tested`, HAG validé).
- Squash-merge :
  - `client-mobile` : `7e27bd0` (PR #20 closed) — branche distante
    `feat/task-115-refonte-stitch-mail-list` supprimée, branche locale conservée.
- `develop` CI : aucun workflow configuré sur le repo `HealthPlatform.Mobile`
  (rien à vérifier — rule 5 N/A).
