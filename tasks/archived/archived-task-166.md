# todo-task-166.md — Chat IA mobile : rendu des tableaux Markdown (GFM)

**Repos**: client-mobile
**Dependencies**: —
**Epic**: E012

## Objective

Dans le **chat IA** de l'app mobile (`mss-ai-chat`), le Markdown est bien rendu
(titres, gras, italique, listes) **sauf les tableaux** : un tableau GFM
s'affiche en texte brut avec des pipes au lieu d'un vrai tableau. Ajouter le
rendu des tableaux à la chaîne de rendu Markdown partagée.

## Cause racine (identifiée)

Le rendu passe par l'util maison
[markdown.util.ts](../../Client/Mobile/src/app/core/utils/markdown.util.ts)
(`markdownToHtml`), un mini-parser regex **escape-first (anti-XSS)** qui couvre
`# ## ###`, `**gras**`, `*italique*`, listes `- `, paragraphes et `<br>` — mais
**pas les tableaux GFM**. Une syntaxe :

```
| Analyte | Valeur | Réf |
|---------|--------|-----|
| Na+     | 140    | 135-145 |
```

n'est reconnue par aucune règle : les lignes retombent dans le remplacement
`\n` → `<br>` et s'affichent en texte brut (pipes visibles).

L'util est **partagée** par le chat IA (`mss-ai-chat`) **et** la synthèse IA
(`mss-mail-summary`) — un seul fix corrige les deux surfaces.

Piège d'implémentation : le parsing de tableau doit se faire **avant** le
collapsing des sauts de ligne (`\n{2,}` → `</p><p>` et `\n` → `<br>`) et le bloc
`<table>` produit ne doit **pas** être ré-enveloppé dans `<p>` ni cassé par les
`<br>`. L'approche escape-first (échappement `& < >` d'abord) doit être
conservée : le HTML de tableau est produit **par l'util**, jamais injecté depuis
la source IA.

## Comportement attendu

1. **Tableaux GFM rendus** : une ligne d'en-tête + une ligne séparateur
   (`|---|:--:|`) + N lignes de corps produisent un vrai
   `<table><thead>…</thead><tbody>…</tbody></table>`.
2. **Formatage inline dans les cellules** : `**gras**`/`*italique*` continuent
   de fonctionner à l'intérieur des cellules.
3. **Alignement** : les marqueurs `:---`, `:--:`, `---:` sont honorés (gauche /
   centre / droite) — best-effort, à défaut alignement par défaut.
4. **Lisible sur mobile** : un tableau plus large que l'écran (390 px) défile
   horizontalement dans son conteneur (`overflow-x`), sans casser la mise en
   page du chat.
5. **Anti-XSS préservé** : contenu échappé d'abord ; aucune balise de la source
   IA n'est interprétée.
6. **Non-régression** : titres, gras, italique, listes, paragraphes rendus comme
   avant, dans le chat IA **et** la synthèse IA.

## Definition of Done

- [ ] Build passe (`npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] `markdownToHtml` rend un tableau GFM en `<table>` (en-tête + séparateur + corps) — test unitaire
- [ ] Formatage inline (`**`/`*`) fonctionne dans les cellules — test unitaire
- [ ] Alignement `:---` / `:--:` / `---:` honoré — test unitaire
- [ ] Un tableau sans séparateur valide n'est PAS transformé (reste du texte) — test unitaire (pas de faux positif sur du texte contenant des `|`)
- [ ] Anti-XSS : une source contenant `<script>`/HTML n'ouvre aucune balise, y compris dans un tableau — test unitaire
- [ ] Non-régression : titres/gras/italique/listes/paragraphes inchangés — tests unitaires existants verts
- [ ] Style tableau + `overflow-x` scroll appliqué (chat IA lisible à 390 px) ; `data-testid` sur le conteneur de message si pertinent
- [ ] Aucune donnée de santé en clair dans les logs client

## Manual Test Plan

- Lancer le mobile : `cd Client/Mobile && npm start` (session e-CPS valide), ouvrir un mail puis le **chat IA**
- Poser une question dont la réponse contient un tableau (ex. « présente les résultats de biologie sous forme de tableau »)
- Attendu : le tableau s'affiche en grille (en-têtes, lignes, alignements), pas en texte brut avec des pipes
- Vérifier un tableau large → défilement horizontal dans la bulle, pas de débordement de l'écran
- Vérifier que gras/italique/titres/listes restent corrects dans la même réponse
- Vérifier la synthèse IA (`mss-mail-summary`) : un résumé contenant un tableau est aussi bien rendu

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR — amélioration d'affichage d'un composant existant (E012)
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — rendu d'affichage, aucune manipulation d'identité patient
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — rendu Markdown côté client, aucun échange
- **Tracé PGSSI-S** : non applicable
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun (le *contenu* d'un tableau de biologie peut citer LOINC/NABM, mais le rendu est agnostique)
- **Hébergement HDS** : non applicable — rendu client
- **AIPD / impact RGPD** : inchangé

## Branches
- `client-mobile` (pushed) : fix/task-166-markdown-tables — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-166-markdown-tables

## Develop log

- Repos touched : `client-mobile`
- DTOs published : no DTO change
- Interop published : no interop change
- Approche : extension de l'util partagée `markdown.util.ts` (`markdownToHtml`) —
  parsing GFM (en-tête + séparateur + corps) **avant** le collapsing des sauts
  de ligne, tableau extrait vers une sentinelle NUL isolée de tout `<p>`/`<br>`,
  puis ré-injecté ; escape-first anti-XSS conservé (HTML de tableau produit par
  l'util). Formatage inline + alignement (`:---`/`:--:`/`---:`) dans les cellules.
  Style `.md-table` + `overflow-x` (scroll 390 px) ajouté aux deux surfaces
  consommatrices (`ai-chat`, `mail-summary`).
- Commits :
  - client-mobile : e7348b8 fix(mobile): rendu des tableaux GFM dans markdownToHtml (chat IA + synthèse)
- Local build / test : ✓ `npm run build` 0 erreur ; `npm test` 760/760 verts (dont 16 nouveaux specs `markdown.util.spec.ts`)
- DOD self-check :
  - Build 0 erreur ✓
  - Tests 0 échec ✓
  - `<table>` (thead+separator+tbody) rendu ✓ (test unitaire)
  - Formatage inline dans cellules ✓ (test unitaire)
  - Alignement `:---`/`:--:`/`---:` ✓ (test unitaire)
  - Pas de faux positif (`|` sans séparateur / séparateur invalide) ✓ (tests unitaires)
  - Anti-XSS y compris dans un tableau ✓ (test unitaire)
  - Non-régression titres/gras/italique/listes ✓ (tests unitaires + suite complète verte)
  - Style + `overflow-x` + `data-testid="markdown-table"` ✓
  - Rendu visuel réel du tableau à 390 px → déféré au test manuel (HAG)
- Next step : /forge-simplify 166

## Simplify log
- Repos passed : `client-mobile`
- Applied & committed : —
- No change : `client-mobile` — util déjà factorisée en helpers unitaires
  (`extractTables`/`splitRow`/`alignmentOf`/`buildTable`/`renderInline`), pas de
  réemploi disponible (aucun renderer de tableau préexistant), pas de code mort.
  SCSS : le bloc tableau est répété dans les deux consommateurs, mais le repo
  duplique déjà les styles markdown par composant (h1/h2/h3, ul, strong) — une
  extraction romprait la convention établie et déborderait du code frais.
- Rolled back (validation RED) : —
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Build / tests : ✓ (inchangés depuis /develop — aucune édition simplify)
- Next step : /lint-mobile 166 (api-mail & client-angular non touchés)

## Lint mobile log
- Mode : A (chaîné)
- Baseline : `ng lint` → **All files pass linting** (0 erreur, 0 warning)
- Itérations : 0 (rien à corriger — code frais 100 % TS/SCSS, aucun template Angular)
- Fixes committés : —
- Résiduel accepté : aucun
- Build / tests : verts (inchangés depuis /develop)
- Next step : /verify-visual 166

## Visual verify log
- skipped — no screen touched : la task modifie l'util de rendu partagée
  `markdown.util.ts` + le style tableau de deux composants existants
  (`ai-chat`, `mail-summary`), sans créer ni réécrire d'écran (aucun
  `## Stitch design log`). Le rendu réel des tableaux dans le chat IA et la
  synthèse est vérifié au test manuel (HAG) — cf. `## Manual Test Plan`.
- Next step : /review 166

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/60 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : **APPROVED** (2 commits, 4 fichiers, 1 blocage corrigé pendant la review, 0 restant)
- Build ✓ (`npm run build`, 0 erreur) — Tests ✓ 761/761 (dont 17 specs `markdown.util.spec.ts`)
- DOD : tous les items command-vérifiables ✓ ; rendu visuel réel déféré au test manuel (HAG)
- Bug attrapé en review : ré-injection du tableau via string de remplacement
  (`String.replace` interprète `$&`/`$$`) → cellule contenant un `$` corrompue.
  Corrigé (remplacement par fonction) + test de régression, commit `a485c03`.
- Sécurité : escape-first anti-XSS conservé ; alignement issu d'un ensemble
  fermé → pas d'injection via `style`.
- Qualité : /sonar skipped — api-mail non touché. /verify-visual skipped — aucun écran.
- Commits : e7348b8 (feature + tests + styles), a485c03 (fix `$` + test)

## Merged
- Date : 2026-07-17 (HAG validé par l'humain — `--i-tested`)
- `client-mobile` : squash commit `76b383a` sur `develop` (PR #60 mergée + fermée)
- Branche distante `fix/task-166-markdown-tables` supprimée (locale conservée)
- develop CI : ✓ vert — https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/29602442241
- Staging : aucune (task lancée en standalone, hors batch /forge)
