# task-349 — /review : CHANGES REQUESTED (chaîne arrêtée avant les PRs)

**Date** : 2026-10-01. **Étape** : `/review`. **Nature** : revue de code bloquante. Ce n'est ni un
build, ni un test, ni l'e2e : tout cela est vert (voir plus bas).

Je n'ai rien commité, rien poussé et ouvert aucune PR. La task reste en `wip-*`. Le code-only
Angular n'est pas touché par la forge.

## Validation (verte)

| Repo | Build | Tests |
|---|---|---|
| api-mail | ✅ | ✅ domain 190, infra 677, application 3311, api 1151, intégration 678 (16 sautés). Les 3 échecs « fenêtre 22-24 h UTC » vus pendant /develop passent à 06 h UTC : ils sont bien liés à l'heure |
| client-blazor | ✅ 0 warning | ✅ 372 (2 sautés) |
| client-mobile | ✅ | ✅ 967/967 |
| client-angular | ✅ weda2 | ✅ 11 projets |
| dtos-mss | ✅ | n/a |

Le `## E2E log` est vert : 2 voies à 25/25, parité verte, et E2E-COMPOSE-002 passe rouge par mutation
sur les deux clients.

## Points bloquants, vérifiés dans le code

### B1 — api-mail · la garde accepte une valeur AJOUTÉE par le modèle
`src/Application/Helpers/SpellingCorrectionGuard.cs`, `KeepsProtectedTerms` (l. 118-137).

- Le contrôle ne va que dans un sens : chaque terme protégé de l'original doit figurer dans la
  sortie. Rien ne vérifie l'inverse.
- Conséquence : un modèle qui ajoute « Puis 150 mg. » à une phrase de ~22 mots reste dans les marges
  de reformulation, et obtient le verdict `Accepted`.
- C'est le même trou qui laisse passer une réponse « ```html…```\nJ'ai corrigé 2 fautes. »
  (`Unwrap` ne retire la clôture qu'en toute fin).
- **Correctif** : faire le contrôle multiset dans les deux sens. Test rouge d'abord : une posologie
  insérée doit donner `ProtectedTermChanged`.
- **Gravité** : une posologie inventée serait proposée au praticien, dans un courrier médical.

### B2 — client-angular · la signature part au fournisseur quand son contenu n'est pas dans un `<p>`
`ui/html-editor/mss-role.extension.ts` et `core/utils/spelling-correction.util.ts` (`signatureBlock`).

- Tiptap n'a aucune règle pour `<div data-mss-role="signature">`. Le contenu inline est alors
  enveloppé dans un paragraphe qu'il crée lui-même, sans le rôle.
- Le relecteur l'a reproduit sous jsdom avec une signature créée sur mobile, du type
  `Dr X<div>Cardiologue</div>`.
- `splitOwnText` et `ownTextEnd` ne trouvent alors plus de borne : toute la signature (identité, RPPS,
  téléphone) est envoyée. Cela enfreint la règle « jamais la signature ».
- **Correctif** : un nœud Tiptap dédié (`div[data-mss-role]`, contenu `block+`), ou `<p>` autour du
  contenu inline dans `signatureBlock`. Test : une signature inline survit à une frappe et n'est pas
  envoyée.
- **Récidive** de `conventions/angular.md` › `tiptap-commentaires-perdus` : passer le compteur à 2.

### B3 — client-blazor · « Appliquer » écrase un texte modifié pendant la correction
`NewMailComponent.razor`, `OnApplySpellingAsync`, branche du corps entier (`whole.Replacement`).

- Le composant ne fait aucun contrôle d'instantané. Le mobile et l'Angular, eux, refusent avec
  « texte modifié ».
- Scénario : le praticien tape ou dicte pendant que l'aperçu est ouvert, puis clique sur
  « Appliquer ». Sa nouvelle phrase est perdue, et une signature changée entre-temps revient à
  l'ancienne.
- **Correctif** : comparer `SplitOwnText(BodyHtml).Own` au texte envoyé, et refuser avec un message
  si ce texte a changé. Test bUnit.

### B4 — client-blazor · une sélection DANS la signature est envoyée
`Src/Component/Shared/wwwroot/js/spellingSelection.js` (`captureSelection`).

- La signature n'est bornée que par des commentaires : `closest('.mss-quote, blockquote')` ne la
  voit pas.
- Une sélection située entre `<!-- signature -->` et `<!-- /signature -->` ne contient aucun
  marqueur, donc `TouchesQuoteOrSignature` la laisse passer.
- **Correctif** : comme sur mobile, situer le début et la fin de la plage par rapport aux nœuds
  commentaires (ou envelopper la signature dans un élément). Test.

### B5 — client-blazor · le flag n'échoue pas fermé sur une réponse non-JSON
`AiService.IsSpellingCorrectionEnabledAsync` → `HttpRequestService.GetCoreAsync`.

- `JsonException` n'est pas attrapée. Une réponse 200 non-JSON (proxy, fallback SPA) fait planter
  `OnInitializedAsync` : c'est tout l'écran de rédaction qui tombe, et pas seulement le bouton qui
  disparaît.
- **Correctif** : try/catch qui rend `false`, comme `CorrectSpellingAsync`. Test.

### B6 — client-angular ET client-mobile · une sélection sur plusieurs paragraphes casse les paragraphes
- **Angular** (`html-editor.component.ts`, `selectionFragment` et `replaceRange`) :
  `doc.slice(from,to)` est sérialisé fermé, puis `insertContentAt` réinsère des `<p>` fermés.
  Simulé : « Bonjour. Les résultat | sont joint. Merci » donne 4 paragraphes.
- **Mobile** (`html-editor.component.ts`, `replaceRange`) : `insertNode` de `<p>…</p><p>…</p>`
  produit des `<p>` imbriqués, qui se cassent au re-parsing.
- **Correctif le plus simple** : refuser une sélection qui couvre plus d'un bloc (message
  « sélection refusée ») ; sinon, réinsérer avec la profondeur ouverte de la tranche. Test sur
  chaque client.

## Suggestions non bloquantes (à traiter si c'est peu coûteux)

- **api-mail**
  - Un texte de 1 à 2 mots peut être vidé (`<p>Bien reçu</p>` → `<p></p>` donne `Accepted`) :
    refuser une proposition sans mots.
  - Le flag est vérifié après la validation, si bien qu'un 400 révèle l'endpoint flag OFF : vérifier
    le flag d'abord.
  - Un `TaskCanceledException` du fournisseur (timeout) remonte en 499 au lieu de 503 : écrire
    `when (!cancellationToken.IsCancellationRequested)`.
  - `TagPattern` `<\s*/?\s*` : rendre le premier `\s*` atomique, et mapper
    `RegexMatchTimeoutException` vers « aucune correction ».
- **Blazor**
  - Double clic pendant l'appel JS `captureSelection` : passer en `Correcting` avant l'appel.
  - `proposal.Html` null avec `Changed=true` : le traiter comme `Unavailable`.
- **Mobile**
  - Course de `loadSpellingFlag` entre deux ouvertures.
  - Défense en profondeur : `DomSanitizer` avant `insertNode`.
- **Tests manquants** (relevés par la revue) :
  - garde : terme inséré, proposition vide ;
  - Angular : signature inline, sélection multi-blocs au niveau de l'éditeur.

## Reprise

Retour à `/develop task-349` sur ces seuls points : test rouge d'abord pour chaque B, puis vert.
Ensuite, rejouer `/sonar` (api-mail), `/lint-angular`, `/lint-mobile`, `/e2e` et `/review`. Aucun
point ne demande d'arbitrage métier. B6 a un choix par défaut raisonnable : refuser la sélection
multi-blocs.

## Ajouté le 2026-10-01 après le rejeu /e2e

- **E2E-COMPOSE-002** : ajouter la précondition « la citation est dans l'éditeur » avant de demander
  la correction (`conventions/e2e.md` › `precondition-du-negatif`). Le premier essai rouge du rejeu
  venait d'un transfert parti sans le message d'origine (clic 80 ms avant le chargement du
  contenu) : c'est un bug du transfert, corrigé par **task-350**, pas par task-349.
- Ordre recommandé : merger task-350 avant de rejouer `/e2e` sur task-349. Sinon, le premier passage
  à froid de COMPOSE-002 peut rester rouge, désormais sur la précondition.

## Deuxième revue, 2026-10-01 — CHANGES REQUESTED (3 nouveaux bloquants)

Validation verte :
- api-mail : 3320 + intégration 678/678 ;
- Blazor : 387 ;
- mobile : 969 ;
- Angular : 11 projets ;
- dtos-mss : build vert ;
- e2e : 2 voies à 25/25, 0 flaky ;
- Sonar : QG OK.

B1, B3, B4, B5 et B6 (mobile et Angular) sont vérifiés corrigés. B2 protège bien la signature, mais il a introduit N1.

### N1 — Angular · le texte d'un NOUVEAU message tombe DANS la signature (régression de B2)
- **Cause** : dans un nouveau message, le corps n'est que `signatureBlock(…)`. Le curseur initial
  (`Selection.atStart`) se pose alors **dans** le nœud `mssRoleBlock`, et ce que tape le praticien
  devient du contenu de la signature.
- **Conséquence** : `splitOwnText` rend un texte vide (« Rien à corriger ») et `ownTextEnd` vaut 0
  (toute sélection est refusée). La fonction ne marche plus sur **tout nouveau message avec
  signature par défaut**. Il n'y a pas de fuite : l'échec est fermé.
- **Correctif** : un paragraphe au praticien **avant** le conteneur de rôle (le `<br/>` d'espacement
  sort du `div`, ou un `<p></p>` le précède).
- **Test** : un nouveau message avec la signature seule ; taper au début ; le texte tapé est bien
  celui qui part à la correction.

### N2 — Blazor · une sélection sur deux lignes « navigateur » passe encore
- **Cause** : Radzen ne fixe pas `defaultParagraphSeparator`, et Chrome écrit
  `Bonjour,<div>Les résultat…</div>`. Une sélection « jour, … Les résultat » ne compte qu'**une**
  balise de bloc : elle est acceptée, et l'application coupe la ligne en deux.
- **Correctif** : comme sur mobile, comparer dans `captureSelection` le bloc englobant de
  `startContainer` et de `endContainer`, et rendre `singleBlock` au C#.

### N3 — Angular · le bandeau INS est masqué en plein écran
- **Cause** : `.compose-blocked-banner` est un frère **après** `.compose-inline`
  (`mail-compose.component.html` ~l. 519). En plein écran, la fenêtre (fixed, z-index 900, fond
  opaque) le couvre.
- **Conséquence** : un envoi refusé pour INS non qualifiée l'est **sans explication visible**, alors
  que le message est réglementaire.
- **Correctif** : placer le bandeau dans `.compose-inline`.

### Suggestions à traiter dans la même reprise
- **Échap** : il ferme un menu Modèle/Signature **et** quitte le plein écran du même coup, y compris
  derrière une confirmation. L'ignorer si un menu ou une confirmation est ouvert.
- **F7** : l'ignorer si une confirmation est ouverte.
- **Blazor** : remettre `_spelling` à l'état initial si `captureSelection` lève autre chose qu'une
  `JSException` (bouton figé sinon).
- **Garde-fou** : documenter que « helene » → « Hélène » est refusé (échec sûr).
- **Angular** : `aria-label` sur les boutons icônes plein écran et ✕.
- **Rappel humain** : les deux `environment.ts` de travail pointent `mssApiUrl` sur
  `https://localhost:7012`. Ne pas les commiter.

### Reprise
`/develop task-349` sur N1, N2 et N3 (test rouge d'abord pour chacun) et les suggestions, puis
`/lint-angular` → `/e2e` (voie Angular) → `/review`. `/sonar` n'est pas à rejouer :
api-mail est inchangé.
