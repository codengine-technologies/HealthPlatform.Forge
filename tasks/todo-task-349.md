# todo-task-349.md — Corriger l'orthographe d'un message avant de l'envoyer, sur les trois fronts : aperçu des corrections, validation par le praticien, jamais de reformulation

**Repos**: api-mail, client-angular, client-mobile, client-blazor
**Dependencies**: — (aucune ; task-325 fera passer la correction sur le modèle local sans changement de cette US)
**Epic**: E009
**Single frontend**: false
**Priorité**: **3** — aide à la rédaction attendue dans toute messagerie. Un courrier médical avec des fautes nuit à la crédibilité du praticien auprès de ses confrères et de ses patients.

> **Origine.** Analyse des manques fonctionnels du client Angular du 2026-09-30 (session forge,
> à la demande du responsable produit). La route serveur de correction existe mais n'est appelée
> qu'après une dictée vocale, et seulement dans Blazor. Règles métier arbitrées par l'humain le
> même jour : flag désactivé en production, aperçu puis validation, sélection sinon texte du
> praticien, orthographe seule.

## Ce qui existe (develop @ `37b3976`, Angular @ `feature/nova-rewriting-mss`)

1. **Serveur** — `POST api/v1/Ai/correct-text` (`Api/Mail/src/Api/Controllers/V1/AiController.cs:48`),
   réponse en flux SSE, service `AiTextService.CorrectTextStreamingAsync`
   (`Api/Mail/src/Application/Services/Implementation/AiTextService.cs:67-90`). Son prompt est
   **dédié à la dictée vocale** (`:23-48`, « Corrige et mets en forme ce texte **dicté** ») : il
   convertit « virgule », « à la ligne » en ponctuation et **restructure** le texte. Il prend et
   rend du **texte brut** : la mise en forme HTML d'un message rédigé serait perdue. Il n'est donc
   pas utilisable tel quel pour corriger un message écrit.
2. **Blazor** — n'appelle `correct-text` que pour la dictée (`NewMailComponent.razor:654-681`) ;
   aucun bouton de correction du texte saisi.
3. **Angular** — aucune correction du message. L'IA « Améliorer / Reformuler » (`improve-text`)
   n'existe que dans l'éditeur de modèles (`libs/mss/src/features/templates/mss-templates.component.ts:377`).
   Seul le correcteur natif du navigateur est actif (task-085, `html-editor.component.ts`).
4. **Mobile** — aucune correction.
5. **Fournisseur** — le chat IA passe aujourd'hui par OpenAI `gpt-4o-mini` via Semantic Kernel.
   task-325 le bascule en local (Ollama) ; son analyse HDS établit que les contenus de mails
   transmis à OpenAI sortent du périmètre HDS, et que l'usage en production reste à qualifier.
6. **Flags** — Flagsmith, catalogue `Api/Mail/src/Application/Constants/FeatureFlags.cs`, semé par
   `Api/Mail/src/AppHost/FlagsmithSeeder.cs` ; chaque front a déjà un service de flags
   (`dashboard-widget-flags.service.ts` en Angular et en mobile).

## Objective

Dans la rédaction d'un message, le praticien demande « Corriger l'orthographe ». Il voit le texte
corrigé, avec les modifications mises en évidence, puis décide d'**appliquer** ou d'**annuler**.
La correction ne reformule jamais : elle rectifie l'orthographe, la grammaire, les accords, la
ponctuation et la typographie, et laisse intacts le vocabulaire médical, les médicaments, les
posologies, les chiffres, les unités, les noms propres et la mise en forme. La fonction existe sur
les trois fronts, avec le même comportement.

### Règles métier (arbitrées le 2026-09-30)

1. **Déclencheur** : une action « Corriger l'orthographe » dans la barre d'outils de la rédaction,
   sur les trois fronts.
2. **Texte corrigé** : le passage **sélectionné** s'il y en a un ; sinon **tout le texte rédigé par
   le praticien**. Ne sont **jamais** corrigés ni envoyés au service : la citation du message
   d'origine (réponse, transfert) et la signature.
3. **Aperçu puis validation** : rien n'est modifié sans l'accord du praticien. L'aperçu met en
   évidence chaque modification ; « Appliquer » remplace le texte, « Annuler » le laisse intact.
   Sans correction nécessaire, le praticien en est informé (« Aucune correction proposée ») et le
   texte n'est pas touché.
4. **Orthographe seule** : jamais de reformulation, de réordonnancement, d'ajout ni de suppression
   d'idée. Termes médicaux, noms de médicaments, posologies, valeurs numériques, unités, dates,
   noms propres, adresses, INS et identifiants restent **identiques caractère pour caractère**.
   La mise en forme (gras, italique, listes, liens, retours à la ligne) est conservée.
5. **Disponibilité** : derrière un feature flag dédié (`ai_text_correction`), **désactivé par défaut
   en production** tant que le fournisseur d'IA n'est pas qualifié HDS (US de l'EPIC E017). Il est
   actif en développement et au banc. Flag désactivé : l'action n'apparaît pas.
6. **Dictée vocale inchangée** : la correction après dictée de Blazor garde son comportement actuel
   (ponctuation dictée, mise en forme).
7. **Échec ou indisponibilité du service** : message clair (« La correction n'est pas disponible
   pour le moment »), le texte n'est pas modifié. Pas de relance silencieuse.
8. **Pendant la correction** : l'action montre un état en cours ; le praticien peut l'abandonner,
   et son texte n'est pas modifié.

### Périmètre

1. **Serveur** : une correction de texte **rédigé** distincte de la correction de dictée. Elle
   applique la règle 4, conserve le HTML de mise en forme, et le service vérifie que les éléments
   protégés de la règle 4 sont intacts dans la réponse. S'ils ne le sont pas, il ne propose pas la
   correction. Contrôle du flag côté serveur (flag désactivé → refus explicite en `ProblemDetails`,
   règle 12). Aucun contenu journalisé.
2. **Flag** `ai_text_correction` ajouté au catalogue et au seeder AppHost (actif en local).
3. **Angular** (`client-angular`, code-only) : action dans la barre d'outils du compose, aperçu avec
   différences mises en évidence, Appliquer / Annuler, sélection sinon texte hors citation et
   signature (la citation est repérée par `QUOTE_MARKER`, `libs/mss/src/core/utils/quoted-body.util.ts`
   sur `feature/nova-rewriting-mss`).
4. **Mobile** (`client-mobile`) : même parcours, adapté à l'écran mobile. Le design de l'aperçu
   passe par la sous-étape `/stitch-design` de `/develop`.
5. **Blazor** (`client-blazor`) : même parcours dans `NewMailComponent`, sans régression de la
   dictée vocale.

### Hors périmètre

- La bascule du fournisseur vers un modèle local (task-325), et la qualification HDS du fournisseur
  en production (US E017 à venir) : cette US ne change pas de fournisseur.
- La correction au fil de la frappe (soulignement mot à mot) : le correcteur natif du navigateur
  reste en place.
- La reformulation ou l'amélioration du style d'un message.
- La correction de l'objet du message.

## Definition of Done

- [ ] Build passes (0 errors) sur les 4 repos ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Serveur** — tests unitaires, rouges d'abord :
  - [ ] un texte fautif rend un texte corrigé, sa mise en forme HTML conservée
  - [ ] une posologie, un nom de médicament, une valeur numérique et une unité présents dans le texte
        sont retrouvés identiques dans la réponse ; si le modèle les altère, aucune correction n'est proposée
  - [ ] flag `ai_text_correction` désactivé → refus explicite, aucun appel au fournisseur
  - [ ] la correction de dictée existante rend le même résultat qu'avant (non-régression)
- [ ] **Serveur** — test d'intégration de l'endpoint de correction (règle 1b) : cas nominal, et
      fournisseur en échec → `ProblemDetails` sans détail technique
- [ ] Flag `ai_text_correction` au catalogue `FeatureFlags.cs` et au seeder AppHost
- [ ] **Angular** — tests de composant : action masquée flag désactivé ; sélection corrigée seule ;
      sans sélection, ni la citation ni la signature ne sont envoyées ; Appliquer remplace ;
      Annuler laisse intact ; échec → message, texte intact
- [ ] **Mobile** — mêmes tests de composant que l'Angular
- [ ] **Blazor** — tests de composant : même parcours ; la dictée vocale garde son comportement
- [ ] Scénario **E2E-COMPOSE-002** (v1, `mobile: requis`, `angular: requis`) ajouté dans
      `Api/Mail/e2e/scenarios.yml` et implémenté dans les deux clients : « le praticien fait
      corriger son texte, voit les corrections, les applique, puis envoie ; le destinataire reçoit
      le texte corrigé, la citation d'origine intacte ». Fournisseur : le faux fournisseur scripté
      du filet (comme E2E-AI-001).
- [ ] `data-testid` sur chaque élément interactif ajouté (action, Appliquer, Annuler, aperçu) ;
      libellés FR en dur (Angular, mobile) / Localizer (Blazor)
- [ ] Aucune donnée de santé dans les logs : ni le texte envoyé, ni le texte corrigé (longueur et
      durée seulement)
- [ ] Événement d'audit « correction demandée » (horodatage, boîte, longueur), sans contenu

## Manual Test Plan

1. Backend : `cd Api/Mail && dotnet run --project src/AppHost` (flag `ai_text_correction` actif en
   local) ; Angular : `cd Client/Angular/front && npm start` ; mobile : `cd Client/Mobile && npm start` ;
   Blazor : `cd Client/Blazor && dotnet run --project <projet Shell>`.
2. **Correction complète** (sur chaque front) : nouveau message, saisir « Je vous adresse mon patient
   pour avi. Il prend du Kardégic 75 mg, 1 cp/jour depuis 3 mois. Les résultat sont joint. », cliquer
   « Corriger l'orthographe » → l'aperçu propose « avis », « résultats », « joints », avec les
   modifications mises en évidence ; « Kardégic 75 mg, 1 cp/jour » et « 3 mois » sont inchangés.
   Appliquer → le texte est remplacé.
3. **Annuler** : même texte, « Corriger l'orthographe », puis Annuler → texte strictement identique.
4. **Sélection** : sélectionner seulement la dernière phrase, corriger → seule cette phrase est
   proposée et modifiée.
5. **Réponse** : répondre à un message, écrire un texte fautif au-dessus de la citation, corriger →
   la citation et la signature ne changent pas.
6. **Mise en forme** : texte avec un mot en gras et une liste à puces, corriger, Appliquer → gras et
   liste conservés.
7. **Rien à corriger** : texte sans faute → « Aucune correction proposée », texte intact.
8. **Flag désactivé** : désactiver `ai_text_correction` dans Flagsmith local, recharger → l'action
   n'apparaît sur aucun front.
9. **Service indisponible** : couper l'accès au fournisseur d'IA → message « La correction n'est pas
   disponible pour le moment », texte intact.
10. **Dictée (Blazor)** : dicter une phrase avec « virgule » et « à la ligne » → même résultat qu'avant.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — messagerie MSSanté intégrée au logiciel ; fonction de confort, non exigée par le DSR
- **Exigences DSR honorées** : non applicable — aide à la rédaction hors exigences DSR ; ne modifie ni le contenu ni les en-têtes MSSanté émis, puisque le praticien valide le texte avant l'envoi
- **INS** : non applicable — aucune INS manipulée par la fonction. Si une INS figure dans le texte, elle est protégée par la règle 4 (restituée à l'identique) et n'est jamais journalisée
- **Authentification PS** : inchangée — PSC / e-CPS de la session de rédaction ; l'envoi reste soumis aux contrôles MSSanté existants
- **Habilitations** : inchangées (fonction de la boîte sélectionnée du praticien)
- **Interop CI-SIS** : non applicable — aucun document CDA ni échange CI-SIS produit ; seul le corps texte du message est concerné
- **Tracé PGSSI-S** : événement « correction demandée » (horodatage, boîte, longueur du texte), **sans contenu** ; conservation alignée sur le journal d'audit existant
- **Consentement patient** : non applicable — aucun partage nouveau avec un tiers au sens du patient. Le texte est transmis au sous-traitant d'IA, ce qui est encadré par le flag et l'AIPD (ligne suivante)
- **Référentiels métier** : aucun (termes médicaux protégés, non normalisés)
- **Hébergement HDS** : **point bloquant pour la production** — le texte rédigé (potentiellement une donnée de santé) est transmis au fournisseur de chat IA, aujourd'hui OpenAI, **hors périmètre HDS** (constat de task-325). D'où le flag `ai_text_correction` **désactivé par défaut en production** jusqu'à la qualification HDS du fournisseur (US E017). En développement et au banc : données synthétiques uniquement
- **AIPD / impact RGPD** : **à mettre à jour** — nouvelle finalité de transmission au sous-traitant d'IA (aide à la rédaction) ; à instruire avec la qualification du fournisseur avant toute activation en production
