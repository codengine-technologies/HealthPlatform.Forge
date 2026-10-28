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
  **Récidive task-352 (extension) — la quatrième, et un piège neuf.** Le paramètre
  `refresh` ajouté à `getFolders()` sans toucher son JSDoc (`require-param`), comme
  sur task-310. Le piège neuf : une méthode **insérée juste avant une autre**, en
  ancrant l'insertion sur la ligne `private refreshFolders(): void {`. Le JSDoc de
  `refreshFolders` se retrouve au-dessus de la nouvelle méthode, fusionné avec le
  sien, et `refreshFolders` n'a plus de bloc (`require-jsdoc`). `--fix` a
  « réparé » les deux erreurs avec des squelettes creux, exactement comme décrit
  plus haut. **Insérer une méthode, c'est l'ancrer avant le JSDoc de la suivante**,
  jamais sur sa signature.
  **Récidive task-353 — la cinquième, et hors de portée du lint.** Le même ancrage sur une
  signature avait déjà orphelin le JSDoc de `deleteFolderElsewhere` dans le support e2e
  **mobile** (extension de task-352), où aucune règle `jsdoc/*` ne tourne : rien ne l'a signalé,
  c'est une relecture qui l'a vu. Et dans `problem-details.utils.ts`, le piège a été reproduit
  puis rattrapé avant le lint. **La consigne vaut partout, lint ou pas** : avant d'insérer, lire
  les lignes qui précèdent l'ancre ; si c'est un `*/`, l'ancre est le `/**` du bloc.
  **Récidive task-367 — la sixième : le `@example` vide recopié du voisinage.** Cinq fonctions neuves
  du support e2e Angular (`weda-host.ts`, `e2e-backend.ts`) portaient un `@example` **sans contenu**,
  comme leurs voisines antérieures : 5 warnings `jsdoc/require-example` (« Missing JSDoc @example
  description »). Un `@example` vide n'est pas un exemple, et le style du fichier n'est pas une
  excuse. **Consigne** : le `@example` porte au moins une ligne d'appel, avec le résultat attendu en
  commentaire (`fakeIntentTitle('a1b2') // → '…'`).
- **Origine** : task-304 (/lint-angular, 57 erreurs — 55 auto-fixées, 2
  `require-returns` + 23 squelettes creux repris manuellement) ;
  task-308 (/review, 2 `require-param` sur signatures modifiées) ;
  task-310 (/develop, 3 erreurs + 2 warnings sur un paramètre objet ajouté) ;
  task-352 (/lint-angular, 1 `require-param` + 1 `require-jsdoc` par JSDoc déplacé) ;
  task-353 (/simplify : JSDoc orphelin dans le support e2e mobile, hors lint) ;
  task-367 (/lint-angular, 5 `require-example` sur des `@example` vides) ;
  task-365 (/lint-angular, 1 `require-param` : paramètre `session` ajouté à `fakeAuthProxy`
  du support e2e sans toucher son JSDoc — le même geste que task-308 et task-310)
- **Occurrences** : 12 (task-399 — `chooseSender(scope, sender = { address, delegated })` du support e2e Angular : un paramètre **objet à valeur par défaut** documenté par un seul `@param sender` ; 2 `require-param` (`sender.address`, `sender.delegated`). C'est exactement le détail de task-310, sur une fonction neuve cette fois ; task-375 — `runE2eTool` du support e2e Angular passé de `void` à `string` sans `@returns` (`require-returns`), et deux fonctions neuves (`createMessageElsewhereIn`, `deleteMessageElsewhereIn`) écrites sans leur JSDoc complet au premier jet. Attrapé par le lint ciblé de /develop. **Changer le type de retour, c'est modifier la signature** : le `@returns` suit au même geste ; task-378 — une constante insérée en ancrant sur `function toError<T>(` : le JSDoc de `toError` est passé au-dessus de la constante, la fonction sans bloc. Vu à la relecture du diff avant tout lint ; la consigne de task-352 (« si la ligne précédente est `*/`, l'ancre est le `/**` ») s'applique aussi aux scripts d'édition ; task-379 — une fonction privée à `@example` vide rendue `export` pour être réutilisée : la règle s'applique dès l'export, compléter l'exemple au même geste ; task-374 — un `@example` vide sur un helper e2e, et un `@param` ajouté sans description par l'auto-fixer : le fixer pose la balise, pas son texte ; task-376 — des constantes exportées insérées en ancrant sur `@Component({` : le JSDoc de la classe, juste au-dessus du décorateur, est passé sur les constantes, et la classe s'est retrouvée sans bloc (`require-jsdoc`, deux composants). Attrapé par le lint ciblé de /develop avant tout rendu. **Un décorateur est une signature** : l'ancre est le `/**` qui le précède)

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
  Sur `client-mobile`, la configuration est encore au format `.eslintrc.json` : sans
  `ESLINT_USE_FLAT_CONFIG=false`, ESLint 9 sort en erreur (« couldn't find an eslint.config »)
  et **ne lint rien**. Constaté le 2026-10-02 (task-329).
- **Origine** : task-349 (/develop, passe qualité ; puis /lint-angular : un `http.get<…>(\`${…}\`)`
  ajouté à `mss-api.service.ts` dépassait la largeur ; puis la reprise B1-B6 : `html-editor.component.ts` et `live-ai.e2e.ts`) ;
  task-329 (/develop : 4 lignes ajoutées à `mail-compose.component.ts` au-delà de 100 colonnes,
  attrapées par le lint ciblé **avant** tout commit. Le contrôle imposé ici a fonctionné ;
  reste à écrire au format : couper une ligne dès qu'elle approche 90 colonnes. Puis
  récidive le même jour sur `functional.e2e.ts`, d'où le remède mécanique ci-dessous)
- **Remède mécanique** (task-329) : avant de formater à la main, tester si le fichier était
  propre en HEAD : `git show HEAD:front/<f> | npx prettier --check --stdin-filepath <f>`.
  S'il l'était, `npx prettier --write <f>` ne touche **que** les lignes de la task. Le vérifier
  par `git diff --stat` : les insertions grossissent, aucune suppression n'apparaît hors des
  hunks. Sinon, seulement, formater à la main.
- **Récidive task-331** (/develop, extension 2) : `prettier --write` lancé d'un bloc sur une liste de fichiers dont `audit.model.spec.ts`, qui n'était pas propre en HEAD (47 lignes de diff pour 2 ajoutées). Attrapé par le `git diff --stat` d'après coup, restauré depuis HEAD avant tout commit. Le réflexe à prendre : tester chaque fichier **existant** avec le remède mécanique **avant** de le mettre dans la commande `--write`, jamais après.
- **Occurrences** : 6

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

### service-propre-au-composant — Une promesse ne livre rien à un composant détruit, ni par un chemin partagé
- **Règle** : convention projet (défaut fonctionnel, invisible au lint et aux tests unitaires)
- **Repos** : client-angular (et tout composant qui fournit ses propres services)
- **Piège** : `mss-mail` fournit lui-même `MailEventService` (portée du composant). Il demandait
  l'intention d'envoi de Weda (task-367), puis émettait `openCompose$` à la réponse. Deux défauts,
  vus par l'e2e E2E-WEDA-003 (vert 1 fois sur 3), jamais par les tests unitaires :
  1. la messagerie détruite puis remontée pendant l'attente : l'intention partait dans le service
     de l'instance morte, perdue ;
  2. le chargement du **premier** dossier émet `folderChanged$`, que la messagerie traitait comme
     « le praticien quitte un dossier » : elle demandait la fermeture de la rédaction ouverte.
- **Consigne** :
  - une donnée attendue au-delà de la vie d'un composant vit dans un service **racine** qui la
    garde jusqu'à ce qu'une instance **vivante** la prenne (`take()` mis en cache, `claim()` une
    fois, garde `destroyRef.destroyed`) ;
  - une réaction à un événement partagé (`folderChanged$`, sélection) distingue l'action du
    praticien du chargement initial, **à la source** : ne pas ajouter d'exception dans le
    consommateur (« fermer, sauf si… ») ;
  - un parcours asynchrone d'entrée se rejoue plusieurs fois en e2e avant d'être déclaré vert.
- **Preuve** : tests unitaires `mss-mail.component.compose-intent.spec.ts` (instance détruite pendant
  la préparation ; premier dossier puis dossier suivant), rouges sous mutation du correctif.
- **Origine** : task-367 (/develop, e2e et passe qualité)
- **Occurrences** : 1

### garde-sur-point-d-entree-commun — recenser tous les appelants avant de durcir une entrée partagée
- **Piège** : task-350 ajoute une défense en profondeur à l'ouverture de la rédaction : une réponse
  ou un transfert sans le message d'origine est refusé. Le chemin visé (Répondre / Transférer
  depuis la lecture) est corrigé et testé, mais l'assistant IA mobile (`ai-chat` › `replyToCited`)
  ouvrait lui aussi une réponse, **sans contenu**. La garde l'a transformée en refus systématique.
  Son test ne vérifiait que l'événement émis (`openCompose$.next`), pas l'ouverture : il est resté vert.
- **Consigne** : avant d'ajouter une garde à une entrée partagée (`openCompose$`, un service, un
  guard de route), lister **tous** ses appelants
  (`grep -rn "openCompose\$\.next" src libs`), et pour chacun dire s'il satisfait la nouvelle
  précondition. Un appelant qui ne la satisfait pas est corrigé dans la même task, avec un test
  qui vérifie la donnée transmise, pas seulement l'émission.
- **Preuve** : revue de task-350, CHANGES REQUESTED, puis correctif `d198e10` (client-mobile). Le
  test de l'assistant exige désormais `content` dans la demande d'ouverture. Rouge avant le
  correctif, vert après.
- **Origine** : task-350 (revue)
- **Occurrences** : 1


---

### pdf-en-cadre-sandboxe — Chrome n'affiche pas un PDF dans un cadre sandboxé
- **Piège** : pour cloisonner un HTML reçu (corps de mail, document CDA), on pose `sandbox` sur
  l'`iframe` qui le rend. Un PDF **imbriqué** dans ce cadre (le CDA embarque ses PDF) ne s'affiche
  plus : icône de document cassé avec `allow-same-origin`, cadre blanc sans. Retirer `sandbox` pour
  le garder visible rouvre l'exécution du HTML reçu à l'origine de l'application.
- **Consigne** : le HTML reçu va dans un cadre `sandbox="allow-popups allow-popups-to-escape-sandbox"`
  (jamais `allow-scripts`, jamais `allow-same-origin`) ; ses PDF embarqués en sont **sortis** et
  rendus par le composant hôte, chacun dans son cadre, depuis un blob typé `application/pdf` (un
  blob PDF ne lance que la visionneuse). Tout blob affiché en `iframe` est retypé côté client :
  le type servi pour une pièce vient de l'expéditeur.
- **Preuve** : sonde Chrome de task-368 (cadre sans sandbox : gestionnaire exécuté, PDF visible ;
  sandbox avec et sans `allow-same-origin` : rien d'exécuté, PDF non affiché). Specs
  `medical-html-frame.component.spec.ts` (weda2 et mobile).
- **Origine** : task-368
- **Occurrences** : 1

---

### double-incomplet-erreur-non-geree — Tous les tests verts, mais `npm test` rouge : un double sans la méthode appelée
- **Piège** : un code modifié appelle une méthode d'un service (`login()` sur l'échec d'un échange) que le double d'un spec EXISTANT n'expose pas. L'appel part dans un callback RxJS : l'exception n'échoue aucun test, Vitest la compte en « Unhandled Errors » et la cible `test` sort en échec — vu seulement au `npm test` complet.
- **Consigne** : quand une dépendance gagne un nouvel appel, chercher ses doubles (`grep -rn "provide: {Service}" --include=*.spec.ts`) et les compléter ; lire la ligne `Errors` de Vitest, pas seulement `Tests`.
- **Preuve** : task-370, `/review` : 2 723 verts, 1 erreur non gérée (`this.authenticationService.login is not a function`), cible `weda2:test` en échec ; double complété → vert.
- **Origine** : task-370 ; task-376 (/develop : le double de `MailboxSessionStore` du spec des envois en attente n'exposait pas `failedActionsCount`, lu par le template — 23 rouges d'un coup, vu et complété avant tout commit)
- **Occurrences** : 2

---

### identifiant-adopte-avant-creation — Un identifiant n'est adopté qu'une fois l'objet créé par le serveur
- **Piège** : la rédaction posait l'identifiant de son brouillon (GUID client) dès le premier enregistrement,
  avant la réponse. Un `POST` raté laissait un identifiant que le serveur n'avait jamais vu : tous les
  enregistrements suivants partaient en `PUT` (404), la fermeture perdait le contenu, l'envoi échouait.
- **Consigne** : un identifiant proposé par le client vit à part (`proposedDraftId`) jusqu'au succès de la
  création ; seul le succès l'adopte. Un nouvel essai repropose le même (création idempotente). Une
  fermeture qui enregistre **attend** le résultat, et reste ouverte sur un échec, message affiché.
- **Preuve** : `mail-compose-safety.component.spec.ts` (weda2), rouges sous la mutation « PUT sur un id
  jamais créé » ; même correctif et mêmes tests sur le mobile.
- **Revers (revue de task-376)** : adopter l'identifiant au retour seulement ouvre une course avec
  l'envoi. Un enregistrement en vol au moment d'« Envoyer » fait partir le message par la route d'envoi,
  puis le POST revient et adopte un brouillon **du message déjà parti** (double envoi possible). Toute
  écriture de brouillon en vol est donc neutralisée une fois l'envoi engagé : réponse ignorée, aucune
  recréation `404 → POST`, ou brouillon créé aussitôt retiré. Le test laisse le POST en vol, envoie,
  puis le termine.
- **Origine** : task-376 (audit ANG-16, weda2 et mobile ; course relevée en revue)
- **Occurrences** : 1

### contexte-pose-a-cote — Un contexte posé à côté d'un événement est hérité par l'événement suivant
- **Piège** : « Annuler et remplacer » posait l'original à annuler dans un signal partagé
  (`cancelAndReplaceContext`), puis émettait l'ouverture de la rédaction. Seule la fermeture le vidait :
  un « Nouveau message » ouvert sans fermer partait par `cancel-and-replace` et marquait l'original
  « [ANNULÉ] ».
- **Consigne** : ce qui qualifie une ouverture voyage **dans** l'événement (`ComposePrefill.cancelAndReplace`)
  et vit dans l'état de la rédaction, remis à zéro à chaque ouverture. Jamais un signal partagé « à côté ».
- **Preuve** : test « Annuler et remplacer puis Nouveau message », rouge sous la mutation qui ne remet pas
  le contexte à zéro.
- **Origine** : task-376 (audit ANG-15)
- **Occurrences** : 1

### reponse-sur-instantane — Une réponse asynchrone appliquée sur un instantané écrase la frappe
- **Piège** : l'assistance IA des modèles (générer, améliorer, détecter les champs) et « par défaut » des
  signatures appliquaient leur réponse sur l'objet lu **avant** la requête (`{ ...template, body }`) :
  ce que le praticien avait tapé pendant la demande était écrasé, sans un mot.
- **Consigne** : à la réponse, vérifier que l'objet édité est toujours celui de la demande ; sinon écarter la
  réponse et le dire. Une mise à jour d'un seul champ s'applique sur l'état **courant** (`update`), jamais
  sur l'instantané.
- **Preuve** : `mss-templates.component.spec.ts` / `mss-signatures.component.spec.ts`, rouges sous mutation.
- **Origine** : task-376 (audit ANG-75)
- **Occurrences** : 1

### desabonnement-annule-un-envoi — `takeUntilDestroyed` annule la requête, pas seulement l'écoute
- **Piège** : se désabonner d'un `HttpClient` **annule** la requête. La confirmation d'un envoi mis de côté
  portait `takeUntilDestroyed` : quitter la page en pleine transmission SMTP coupait la confirmation, et
  le message restait peut-être parti.
- **Consigne** : une requête à effet externe irréversible (envoi, confirmation) est souscrite
  indépendamment de la vie du composant (`ReplaySubject` abonné à la requête) ; seule l'écoute de son
  résultat suit le composant.
- **Preuve** : `leavingThePage_DuringAConfirmation_DoesNotCancelIt`, rouge sous la mutation qui rend la
  requête annulable.
- **Origine** : task-376 (audit ANG-26)
- **Occurrences** : 1

---

### tester-a-travers-le-parent — Un correctif d'affichage se teste par la liste que l'écran rend vraiment
- **Piège** : sur le mobile, la lecture d'une pièce homonyme a été corrigée dans `mail-attachment` (rang
  transmis), et testée en donnant au composant les deux pièces directement. Or le parent
  (`mail-detail.mergedAttachments`) dédoublonne sur `guid || fileName`, et le backend ne renseigne pas le
  `guid` des pièces MIME : la seconde pièce n'atteint jamais l'enfant. Correctif mort, tests verts.
- **Consigne** : un comportement d'affichage se prouve depuis la donnée du serveur jusqu'aux lignes rendues
  (le parent qui fusionne, filtre ou dédoublonne compris), pas en alimentant l'enfant à la main. Avant de
  corriger un enfant, lire ce que le parent lui passe.
- **Preuve** : revue de task-376 (CHANGES REQUESTED, B2) ; test à écrire par la reprise, rouge sur le code
  revu.
- **Origine** : task-376 (/review)
- **Occurrences** : 1

---

### reponse-d-un-contexte-depasse — Une réponse ne s'applique qu'au contexte pour lequel elle est partie
- **Piège** : un composant réutilisé pour une autre fiche, un autre document, une autre boîte, reçoit la réponse
  d'une requête partie pour le précédent. Rien n'annule cette requête, et le résultat est appliqué à l'écran
  courant. Constaté sur task-373 : les candidats d'un document A affichés sous les traits du document B (« Rattacher »
  rattache alors B au patient de A, ANG-54) ; la chronologie et l'opposition d'une fiche remplacées par celles de la
  fiche précédente quand elle répondait en dernier.
- **Consigne** : toute requête dont la réponse alimente un état lié à une sélection (`patientId`, document, boîte)
  emporte l'identifiant de cette sélection, et la réponse est ignorée si la sélection a changé
  (`if (this.patient()?.id !== patientId) return`, ou un numéro de chargement). Abandonner la requête précédente
  (`unsubscribe`, `switchMap`) en plus. Les deux protections se testent : la réponse ancienne arrive APRÈS le
  changement de sélection, et l'écran ne bouge pas.
- **Preuve** : `patient-timeline.component.spec.ts` (« ignores the answer of a record that is no longer the one
  shown »), `patient-card.component.spec.ts`, `patient-attachment-dialog.component.spec.ts` (ANG-54), rouges sous
  mutation (M3, M9b).
- **Origine** : task-373 (audit ANG-50, ANG-54)
- **Occurrences** : 1

### chainage-optionnel-qui-ment — `a?.b` suivi de `not.toBeNull()` passe quand `a` est absent
- **Règle** : convention projet
- **Repos** : les deux
- **Piège** : `expect(column?.querySelector('#champ')).not.toBeNull()` passe quand `column` n'existe pas, car le
  chaînage optionnel rend `undefined`, qui n'est pas `null`. Constaté sur task-388 : le test « la fiche tient sur deux
  colonnes » passait avant que les colonnes existent.
- **Consigne** : un test qui cherche dans un conteneur exige d'abord ce conteneur (`expect(column).toBeTruthy()`),
  puis utilise `toBeTruthy()` pour l'élément cherché. Ne jamais combiner `?.` et `not.toBeNull()` sur un élément
  attendu. Voir le test rouge avant de le croire vert.
- **Preuve** : `mss-contacts-render.component.spec.ts` (j), vert sans les colonnes avec l'ancienne assertion, rouge
  avec la nouvelle, vert une fois les colonnes posées.
- **Origine** : task-388 (/develop) ; task-393 (/develop, weda2)
- **Occurrences** : 2 (task-393 — variante Vitest : `expect(undefined).toContain(x)` passe aussi. Le test « la route
  `contacts` porte la garde de sortie » était vert sans la garde, parce qu'il lisait `route?.canDeactivate`. Exiger
  la route, puis `Array.isArray(route.canDeactivate)`, avant `toContain`.)

### ds-button-id-requis — `ds-button` sans `id` fait tomber tous les tests de rendu du composant
- **Règle** : convention projet (contrat du design system weda2)
- **Repos** : client-angular
- **Piège** : `ds-button` déclare `id` en `input.required`. Un seul bouton ajouté sans `id` lève NG0950 au rendu, et
  **tous** les tests de rendu du composant tombent, anciens compris. Le message ne pointe pas le bouton fautif.
- **Consigne** : tout `ds-button` ajouté porte un `id` unique dès l'écriture (le même que celui que vise un test e2e
  quand il y en a un). Devant une cascade NG0950, chercher d'abord le dernier `ds-button` ajouté.
- **Origine** : task-393 (/develop, weda2)
- **Occurrences** : 1

### action-a-deux-entrees — Une action offerte à deux endroits a un test par point d'entrée
- **Règle** : convention projet
- **Repos** : les deux
- **Piège** : sur task-393, « Écrire » existe sur la ligne du carnet (au survol) et dans l'aperçu. Le choix d'adresse
  n'était rendu que dans l'aperçu du contact sélectionné, et le bouton de la ligne ne sélectionnait pas. Depuis la
  ligne, rien ne s'affichait, ou le choix apparaissait sous un autre contact. Les tests ne passaient que par l'aperçu :
  tout était vert.
- **Consigne** : quand une action est offerte à plusieurs endroits (ligne, aperçu, menu, raccourci), écrire un test par
  point d'entrée, avec l'état de départ de ce point (aucune sélection, autre élément sélectionné). Un état affiché à un
  seul endroit (dialogue, sélecteur) ne dépend jamais d'une sélection que l'autre point d'entrée ne pose pas.
- **Origine** : task-393 (/review, CHANGES REQUESTED)
- **Occurrences** : 1

### page-ionic-non-demontee — Une page Ionic rendue en test retombe sur les tests de rendu suivants
- **Règle** : convention projet (instabilité Karma, invisible au lint)
- **Repos** : client-mobile
- **Piège** : sur task-393, un test qui rendait la page du carnet, puis un test qui rendait une fenêtre Ionic
  (`ion-modal`), faisaient tomber d'autres suites une fois sur trois : rendu de la rédaction, sélecteur de messagerie,
  erreurs `onAriaChanged`. Leurs éléments restaient attachés au document après la fin du test.
- **Consigne** : un test Karma qui rend une page Ionic la démonte lui-même (`fixture.destroy()`, puis une courte
  attente). Les libellés d'une fenêtre (`aria-label`, textes) se testent par les méthodes que le gabarit lie, pas en
  rendant la fenêtre. Pour croire une suite stable, la rejouer plusieurs fois (la passe de task-393 : 0 échec sur 6
  après correction, contre 2 sur 6 avant).
- **Origine** : task-393 (/develop, reprise mobile)
- **Occurrences** : 2 (task-375 — après la synchronisation avec `develop`, `MailComposeComponent` a échoué deux passages sur trois, sur deux ensembles différents : suggestions de destinataires de task-388, puis « frappe dans le vrai éditeur » de task-394 ; vert au troisième (1289/1289), sur une task qui ne touche pas la rédaction. Même famille, suite de rédaction non encore démontée proprement : **task de stabilisation à ouvrir**)

### annulation-qui-vide-l-etat-d-un-autre — Une annulation asynchrone ne vide que sa propre donnée
- **Règle** : convention projet (défaut de course, invisible aux tests à un seul appel)
- **Repos** : les deux
- **Piège** : sur task-393, `composeTo` confiait le destinataire à un service racine, puis, si la navigation était
  refusée, vidait le service (`take()`). Sur un double-clic, la première navigation, remplacée par la seconde, se
  résolvait à `false` après le second `offer`, et vidait le destinataire du second clic. La messagerie s'ouvrait sans
  rédaction. Les tests ne faisaient qu'un appel à la fois.
- **Consigne** : un retour asynchrone qui annule ou nettoie un état partagé vérifie que l'état est encore le sien
  (jeton rendu par `offer`, identifiant, numéro de génération) avant de le vider. Le test lance deux appels, puis
  résout le premier après le second.
- **Voir aussi** : `reponse-d-un-contexte-depasse`, `service-propre-au-composant`.
- **Origine** : task-393 (/review, seconde passe)
- **Occurrences** : 1

### complexity — une branche ajoutée à une méthode déjà chargée la fait déborder
- **Règle** : `complexity` (seuil 20, avertissement)
- **Repos** : `client-angular`
- **Consigne** : avant d'ajouter une branche (`if`, `??`, `?.`) à une méthode d'aiguillage comme
  `initializeFromPrefill`, compter ce qu'elle porte déjà. Près du seuil, sortir d'abord un bloc
  existant dans une méthode nommée et documentée (`applyPrefillRecipients`, `resumeDraft`), puis y
  ajouter la branche. Un avertissement n'arrête pas le pipeline : c'est pour ça qu'il s'accumule.
- **Origine** : task-399 (/lint-angular, 1 avertissement neuf : `initializeFromPrefill` de 20 à 24
  par la reprise de brouillon délégué et la base de « Répondre à tous » ; corrigé par extraction.
  `replacePlaceholders`, déjà à 44 avant la task, passe à 45 : dette antérieure, laissée)
- **Occurrences** : 1

### lecture-decidee-a-l-init-sur-un-etat-de-session — une lecture conditionnée à la session part au passage en ligne
- **Règle** : convention projet (défaut fonctionnel trouvé par `/develop` au banc e2e, E2E-MAILBOX-003)
- **Repos** : les deux
- **Consigne** : une lecture qui dépend d'un état de session (en ligne / hors ligne, boîte courante) ne se décide
  **pas** dans `ngOnInit` ou le constructeur sur la valeur du moment : à l'arrivée directe sur un écran (rechargement,
  lien profond), cet état n'est pas encore résolu. La déclencher dans un `effect` qui observe l'état, une seule fois
  (drapeau), l'appel lui-même dans `untracked`. Le test de composant couvre l'état d'abord défavorable puis favorable.
- **Origine** : task-402 (`/develop`, banc e2e : « Mes boîtes » restait « en chargement » sur la gestion des
  messageries, mobile et weda2)
- **Occurrences** : 1
