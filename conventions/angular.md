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

### jsdoc/require-jsdoc — JSDoc complet sur chaque méthode (client-angular)
- **Règle** : `jsdoc/require-jsdoc`, `jsdoc/require-returns`, `jsdoc/require-param`
- **Repos** : `client-angular` uniquement (la config ESLint de `client-mobile`
  ne porte pas ces règles)
- **Consigne** : écrire le JSDoc **en même temps que la méthode**, jamais après.
  Toute méthode — y compris `protected`, y compris un one-liner comme
  `toggle()` ou un `private baseUrl()` — porte une description, un `@param` par
  paramètre, un `@returns` si elle rend autre chose que `void`, et un
  `@example`. Voir le `CLAUDE.md` de `Client/Angular`, section « JSDoc
  Requirements ».
  **Pourquoi ne pas s'en remettre à `--fix`** : l'auto-fixer *satisfait* la
  règle en insérant un squelette vide (`/** \n * \n * @example \n */`). Le lint
  passe alors au vert sur une documentation qui ne dit rien — pire qu'une
  absence, puisqu'elle fait croire que la méthode est documentée. Et le
  squelette ne couvre pas `@returns`, qui reste en **erreur**. Sur task-304 :
  23 squelettes creux à remplir à la main, dont 2 erreurs résiduelles.
  **Récidive task-308 — et elle est instructive.** Deux erreurs
  `jsdoc/require-param` sur des méthodes dont le JSDoc existait déjà et était
  soigné : en changeant la signature (`Event` → `boolean`, après le passage de
  `<input type="checkbox">` à `ds-checkbox`), le bloc a été conservé tel quel.
  **Modifier une signature, c'est modifier son JSDoc** — le lint ne distingue
  pas un bloc absent d'un bloc périmé, et un `@param` qui ne correspond plus au
  paramètre est un contresens, pas une omission.
  **Récidive task-310 — la troisième, et le même geste.** Un paramètre optionnel
  ajouté à `switchTo(mailbox, options?)` : le JSDoc existant n'a pas suivi, d'où
  3 erreurs d'un coup (`@param mailbox`, `@param options.outgoingAlreadyClosed`,
  `@returns`) puis 2 warnings `require-example`. **Le détail qui manquait à
  cette fiche** : un paramètre objet exige un `@param` par **sous-propriété
  documentée**, noté `@param options.maPropriete` — `@param options` seul ne
  suffit pas, et c'est ce que la rédaction naturelle produit spontanément. Poser
  la règle à l'écriture coûte trois lignes ; la découvrir au lint coûte un
  aller-retour complet build + test.
- **Origine** : task-304 (/lint-angular, 57 erreurs — 55 auto-fixées, 2
  `require-returns` + 23 squelettes creux repris manuellement) ;
  task-308 (/review, 2 `require-param` sur signatures modifiées) ;
  task-310 (/develop, 3 erreurs + 2 warnings sur un paramètre objet ajouté)
- **Occurrences** : 3

### mail-content-body — `content.body` n'est pas le texte du mail
- **Règle** : convention projet (défaut fonctionnel, invisible au lint)
- **Repos** : les deux
- **Consigne** : ne jamais citer, afficher ni renvoyer `MailContentDto.body`
  comme texte du message. Une fois le mail enrichi, le backend y concatène le
  `body` de chaque document CDA, qui est une conversion **Markdown pour la
  recherche** (`## [Document: …]`, images en `data:image/…;base64`). Pour une
  citation (réponse, transfert) : `bodyHtml` s'il existe, sinon le texte sans
  les documents, **échappé** avec ses sauts de ligne. Sur `client-angular`,
  passer par `originalBodyHtml` / `buildQuotedBody`
  (`libs/mss/src/core/utils/quoted-body.util.ts`).
  **Réponse et transfert suivent les messageries classiques** (Outlook,
  Gmail, Thunderbird), décision humaine du 2026-09-30 :
  - répondre : « À » = `Reply-To` sinon l'expéditeur ; citation « Le {date},
    {expéditeur} a écrit : » + `<blockquote>` ; **aucune pièce jointe reprise** ;
  - transférer : « À » vide ; en-tête « Message transféré » avec De / Date /
    Objet / À / Cc ; **pièces jointes d'origine reprises** (dont
    l'IHE_XDM.ZIP, seul porteur du document médical) ;
  - la signature se place **au-dessus** de la citation, repérée par
    `QUOTE_MARKER`, jamais par le balisage de la citation ;
  - le curseur s'ouvre **en tête**, au-dessus de la citation : tout contenu
    chargé de l'extérieur passe par `loadContent` de `mss-html-editor`, car
    un `setContent` tiptap nu laisse la sélection en fin de document, donc
    dans la citation ;
  - une réponse ne reprend pas les pièces jointes mais les **mentionne**, à la
    manière d'Outlook : une ligne par fichier en tête de la citation,
    « [Pièce jointe : IHE_XDM.ZIP — {titres des documents}] ». Titres seuls,
    aucune donnée patient ; pas de mention dans un transfert, qui emporte les
    fichiers (décision humaine du 2026-09-30). Sans texte ni pièce jointe, pas
    de `<blockquote>` vide ;
  - objet : « Re: » / « Fwd: » + l'objet **que le praticien voit**, soit le
    titre du document médical quand il remplace l'objet technique
    (« IHE_XDM.ZIP file detected »). Le préfixe n'est jamais empilé
    (`prefixedSubject`). Le fil ne dépend pas de l'objet, il repose sur
    `In-Reply-To` et `References`.
  Le rendu HTML d'un CDA (`medicalDocuments[i].bodyHtml`) est une fonction de
  l'écran de lecture, comme l'aperçu de pièce jointe d'Outlook : il n'entre ni
  dans la citation, ni dans un aperçu de rédaction. (Un aperçu sous l'éditeur a
  été essayé puis retiré le jour même, car aucune messagerie ne fait ça.) Il
  s'afficherait mal de toute façon : tiptap n'a pas d'extension Table et
  retire `<div>`, `<details>` et `<style>`, et le serveur retire `<style>`.
- **Origine** : correctif direct `client-angular` du 2026-09-30, sur la
  branche `feature/nova-rewriting-mss`, hors chaîne. Constat humain : un
  transfert citait le Markdown base64 du CDA et partait sans l'IHE_XDM.ZIP.
  **Même motif encore présent sur `client-mobile`** :
  `mail-compose.component.ts:314` (`req.content?.bodyHtml || req.content?.body`).
- **Occurrences** : 1

### prettier-fichier-existant — Ne jamais reformater tout un fichier existant
- **Règle** : `prettier/prettier` (client-angular)
- **Repos** : client-angular (code-only : l'humain relit le diff avant TFS)
- **Consigne** : `prettier --write` seulement sur les fichiers **créés** par la task. Sur un
  fichier existant, vérifier d'abord `git diff --stat` après coup : un template ou un SCSS
  qui n'était pas propre en HEAD est reformaté **en entier**. Sur task-349, un template de
  419 lignes est passé à 932 lignes de diff, pour 78 lignes réellement ajoutées. Le diff noie
  le changement pour la relecture humaine. Remède : restaurer depuis HEAD
  (`git show HEAD:…`, lecture seule) et réappliquer les seuls ajouts.
  **Revers** : sans `--write`, les lignes **ajoutées** à un fichier existant ne sont formatées
  par personne. Écrire ces lignes à la main au format Prettier du repo (100 colonnes, tab,
  sans point-virgule), puis lire la sortie du lint sur les fichiers touchés et corriger à la
  main **seulement** les erreurs situées dans les hunks de la task. Ne jamais lancer
  `--fix` sur un fichier qui porte du WIP humain. **Avant de déclarer un repo vert**, lancer
  `npx eslint <fichiers touchés>` (e2e compris) : le vert de la suite ne dit rien du format.
- **Origine** : task-349 (/develop, passe qualité ; puis /lint-angular : un `http.get<…>(\`${…}\`)`
  ajouté à `mss-api.service.ts` dépassait la largeur ; puis la reprise B1-B6 : `html-editor.component.ts` et `live-ai.e2e.ts`)
- **Occurrences** : 3

### tiptap-conteneur-capte-le-curseur — Un nœud conteneur en tête de document capte la frappe
- **Règle** : comportement tiptap / ProseMirror (pas une règle lint)
- **Repos** : client-angular
- **Consigne** : un nœud conteneur (`content: 'block+'`) qui marque un contenu **qui n'est pas au
  praticien** (signature, citation) ne doit jamais ouvrir le document. `Selection.atStart` y pose
  le curseur, et ce que le praticien tape devient du contenu du conteneur. Toujours le faire
  précéder d'un paragraphe au praticien. Tester **les deux** cas : texte + conteneur, et conteneur
  seul (nouveau message avec signature par défaut).
- **Origine** : task-349 (/review, 2^e^ passe : le correctif B2 a cassé la correction de tout
  nouveau message signé)
- **Occurrences** : 1

### tiptap-commentaires-perdus — Tiptap retire commentaires et `<div>` dès la première frappe
- **Règle** : convention projet (défaut fonctionnel, invisible au lint)
- **Repos** : client-angular (`mss-html-editor`, Tiptap) ; client-mobile n'est pas concerné
  (son `contenteditable` garde les commentaires)
- **Consigne** : ne jamais repérer un bloc du corps (signature, citation) par un commentaire HTML
  (`<!-- signature -->`, `QUOTE_MARKER`) une fois l'éditeur monté : ils disparaissent au
  premier `onUpdate`. Poser un attribut `data-mss-role` (conservé par l'extension
  `MssRole`), ou repérer la structure (en-tête de citation généré). Et lire un texte de bloc
  **décodé** : une adresse `Dr A <a@…>` y figure en clair, sans `&lt;`.
- **Origine** : task-349 (revue : un en-tête avec adresse n'était pas reconnu)
- **Occurrences** : 1
