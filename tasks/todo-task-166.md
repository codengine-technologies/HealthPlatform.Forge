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
