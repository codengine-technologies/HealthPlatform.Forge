# conventions/angular.md — Conventions de code Angular apprises par la forge

> **Portée** : `client-angular` (Client/Angular/front) et `client-mobile`
> (Client/Mobile) — tout code TypeScript/Angular écrit par la forge.
> **Lu par** : `/develop` (avant d'écrire du code Angular/Ionic).
> **Alimenté par** : `/lint-angular` et `/lint-mobile` (voir protocole).
> **Jamais édité à la main** sauf pour retirer une convention devenue fausse.

## Protocole d'alimentation (agents lint)

À la fin d'un run (Mode A ou B), pour **chaque règle ESLint corrigée
manuellement** (itérations 2..5 — les fixes de l'auto-fixer `--fix` ne
comptent pas : ils sont gratuits) sur du code écrit par `/develop` :

1. Si une entrée existe pour cette règle → incrémenter **Occurrences**,
   ajouter la task à **Origine**.
2. Sinon → créer l'entrée avec le format ci-dessous, `Occurrences : 1`.
3. Une entrée existe dès la **première** correction manuelle : la
   prévention est immédiate, pas de seuil.

`/develop` lit ce fichier avant d'écrire du code Angular : chaque
« Consigne » est un pattern à appliquer d'emblée — une récidive signalée
par lint sur du code frais est un échec de lecture de ce fichier.

## Format d'entrée

```markdown
### {règle-eslint-ou-slug} — {titre court}
- **Règle** : {id ESLint exact, ou "convention projet"}
- **Repos** : {client-mobile | client-angular | les deux}
- **Consigne** : {ce que /develop doit faire d'emblée}
- **Origine** : task-NNN (/lint-mobile ou /lint-angular, N erreurs corrigées)
- **Occurrences** : {n}
```

---

## Conventions actives

### prefer-control-flow — Control flow natif `@if` / `@for` / `@switch`
- **Règle** : `@angular-eslint/template/prefer-control-flow`
- **Repos** : les deux
- **Consigne** : ne jamais écrire `*ngIf` / `*ngFor` / `*ngSwitch` dans un
  template neuf — utiliser directement `@if (...) { }`,
  `@for (x of xs; track x.key) { } @empty { }`, `@switch`. La règle n'a pas
  d'auto-fixer : chaque oubli coûte une itération manuelle de lint. Bonus :
  le control flow natif ne requiert pas `CommonModule` dans les specs.
- **Origine** : task-140 (/lint-mobile, 5 erreurs corrigées manuellement)
- **Occurrences** : 1

### component-selector — Préfixes de sélecteur `app` / `mss`
- **Règle** : `@angular-eslint/component-selector`
- **Repos** : les deux
- **Consigne** : sélecteurs de composants préfixés `mss-` (composants
  miroir MSS) ou `app-` (pages/coquille). Tout autre préfixe est rejeté
  par la config ESLint (alignée sur client-angular).
- **Origine** : task-095 (/lint-mobile, 4 erreurs — résolues par alignement
  de la config, préfixes désormais imposés)
- **Occurrences** : 1

### fr-hardcode — Libellés FR en dur, pas de ngx-translate
- **Règle** : convention projet (pas de règle lint — mais récurrente en review)
- **Repos** : les deux
- **Consigne** : tous les libellés UI en français en dur dans les templates.
  Aucun pipe/service i18n (le module MSS n'utilise pas ngx-translate ;
  Blazor garde son Localizer, pas Angular). Cf. mémoire
  `project_angular_mss_no_ngx_translate`.
- **Origine** : convention gravée avant la création de ce fichier
- **Occurrences** : n/a (préventif)

### data-testid — Attribut de test sur chaque élément interactif
- **Règle** : convention projet (vérifiée par /review via la DOD)
- **Repos** : les deux
- **Consigne** : chaque élément interactif (bouton, input, toggle, segment,
  item cliquable) et chaque région d'état notable (empty state, erreur)
  porte un `data-testid` kebab-case préfixé par l'écran
  (`settings-logout-btn`, `draft-list-empty`).
- **Origine** : convention gravée avant la création de ce fichier
- **Occurrences** : n/a (préventif)
