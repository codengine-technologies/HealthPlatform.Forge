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

## Branches
- `api-mail` (pushed) : feat/task-349-correction-orthographe — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-349-correction-orthographe
- `client-mobile` (pushed) : feat/task-349-correction-orthographe — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-349-correction-orthographe
- `client-blazor` (pushed) : feat/task-349-correction-orthographe — https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-349-correction-orthographe
- `client-angular` (code-only) : forge écrit le code sur la branche courante de `Client/Angular/` (au `/start` : `feature/nova-rewriting-mss`, 7 fichiers de WIP humain non commités) — humain gère branche, commit, push, PR TFS
- `dtos-mss` : aucune branche à `/start` (branche paresseuse, créée par `/develop` seulement si un contrat change)

## Develop log

**Repos touchés** : `dtos-mss` (contrat), `api-mail`, `client-blazor`, `client-mobile`, `client-angular` (code-only).

**Contrat** : `AuditActionType.TextCorrectionRequested = 36`. Branche `dtos-mss` créée à la demande, package **494.0.0** publié par la CI.
- Consommateurs .NET montés en version : api-mail et Blazor.
- Miroirs manuels : Angular (`audit.model.ts`) et libellé Blazor (`AuditActionLabels`).
- La restauration NuGet exige `GH_TOKEN=$(gh auth token)` (mémoire).

**Commits** (branches `feat/task-349-correction-orthographe`, poussées) :
- `dtos-mss` : `f1e99a2` feat(dto).
- `api-mail` : `3818c88d` bump, `46427318` feat(ai), `246ed020` refactor (passe qualité).
- `client-blazor` : `25d61a1` bump, `da72744` feat(compose), `c1da616` refactor (passe qualité).
- `client-mobile` : `1cef207` feat(compose), `36f8fa0` refactor (passe qualité).
- `client-angular` : **non commité** sur `feature/nova-rewriting-mss`, à commiter et pousser sur TFS par l'humain. Fichiers :
  - `e2e/mss-e2e/specs/live-ai.e2e.ts` ;
  - `core/models/audit.model(.spec).ts`, `core/models/spelling-correction.model.ts` ;
  - `core/services/mss-api.service.ts` ;
  - `core/utils/spelling-correction.util(.spec).ts` ;
  - `ui/html-editor/html-editor.component.ts`, `html-editor.models.ts`, `mss-role.extension.ts` ;
  - `features/mail/components/mail-compose/mail-compose.component.{ts,html,scss,spec.ts}` et `mail-compose-spelling.component.spec.ts`.

  Les 7 autres fichiers modifiés de l'arbre sont du travail en cours de l'humain, laissé intact.

**Serveur** :
- `POST api/v1/ai/correct-spelling` (`SpellingCorrectionController`, JSON), distinct de `correct-text` qui sert la dictée.
- `SpellingCorrectionService` :
  - consigne « orthographe seule », HTML conservé ;
  - flag désactivé → 404 ; fournisseur en échec → 503 « La correction n'est pas disponible pour le moment » ;
  - audit sans contenu ; journaux limités à la longueur, au verdict et à la durée.
- `SpellingCorrectionGuard` (règle 4) refuse la proposition si l'un de ces points change :
  - les balises, et **tous** leurs attributs normalisés ;
  - les termes protégés : chiffres, posologies, unités, noms propres, sigles, adresses ;
  - le texte a été réécrit.
- Flag `ai_text_correction` : échec fermé au démarrage à froid, ajouté au seeder AppHost, forcé dans le profil e2e.
- Faux fournisseur : correction scriptée (`SpellingFixes`).

**Fronts**, même parcours sur les trois :
- flag en échec fermé ;
- sélection, sinon texte du praticien, jamais la signature ni la citation ;
- aperçu mot à mot, Appliquer / Annuler, abandon ;
- message clair si le service est indisponible, texte changé pendant la correction non écrasé.
- Spécificités :
  - Angular : extension Tiptap `MssRole`, car Tiptap retire les commentaires ;
  - mobile : l'éditeur borne la sélection au premier nœud de signature ou de citation ;
  - Blazor : helper JS de sélection et classe `mss-quote` sur les citations.

**E2E-COMPOSE-002** (v1, mobile et Angular requis) ajouté au catalogue avant les tests.
- Implémenté dans `live-ai.spec.ts` (mobile) et `live-ai.e2e.ts` (Angular).
- Parcours : transfert de `mail-lu` à Robert, texte fautif au-dessus de la citation, puis corriger, appliquer, envoyer. Le message reçu est relu du serveur : texte corrigé, citation intacte.
- La requête envoyée ne contient pas la citation.
- Les deux fichiers passent le type-check.

**Preuves du rouge** :
- *Garde* : 3 mutations (termes protégés : 9 rouges, balisage : 3, reformulation : 2), puis 3 tests d'attributs rouges avant correctif.
- *Service* : 3 mutations (flag, garde, journal du texte).
- *Endpoint* : 503 muté en 500.
- *Blazor* : 3 mutations (texte entier envoyé, reste non recollé, refus de sélection retiré).
- *Angular* : 4 mutations, puis l'en-tête avec adresse rouge avant correctif.
- *Mobile* : 4 mutations.
- ⚠ **La preuve par mutation d'E2E-COMPOSE-002 reste à faire.** Elle exige les voies e2e, et donc ports 5052… et `bin/Debug` d'api-mail libres. L'AppHost de l'humain (5 réplicas) et Visual Studio les tiennent. Elle sera faite au moment de `/e2e`.

**Passe qualité §Q** (une revue par repo, quatre angles) :
- *Défauts relevés et corrigés* :
  - le garde ignorait les attributs, ce qui ouvrait une injection par sélection ;
  - Angular ne reconnaissait pas un en-tête dont l'expéditeur porte une adresse ;
  - Blazor : un délai dépassé figeait l'aperçu, une réponse illisible faisait planter, la fermeture n'annulait pas ;
  - mobile : une fermeture pendant une correction, et le flag était lu en échec ouvert à la réouverture.
- *Appliqué* :
  - réutilisation (logger partagé, clé `Cancel`, marqueurs uniques) ;
  - un POST silencieux fondé sur le noyau existant au lieu d'une 11e copie ;
  - états fusionnés, diff limité à la fenêtre modifiée ;
  - validation unique dans le service ;
  - S103, S125 et CA1861 dans les tests, jetons de design en SCSS.
- *Écarté* :
  - rôle `quote` posé par `buildQuotedBody` : l'heuristique resterait nécessaire pour les brouillons existants ;
  - lecteur de flags partagé et mis en cache : le service des widgets ne garde que `dashboard_widget_` et reste en échec ouvert ;
  - `RestoreSelection` de Radzen, qui ignore la sélection gardée au mousedown ;
  - factorisation des pas e2e existants.

**Validation** :
- api-mail (Release, `bin/Debug` verrouillé par l'AppHost de l'humain) :
  - domain 190, infrastructure 677, api 1151, application 3311, integration 675 (16 ignorés) ;
  - 3 échecs pré-existants, liés à la fenêtre horaire 22:00–24:00 UTC (« aujourd'hui » local ≠ UTC du Dovecot de test) : aucun fichier de la task n'y touche, ils sont à rejouer après minuit UTC.
- Blazor : 372 passés, 2 ignorés.
- Mobile : 967/967.
- Angular : 510 et 2575 passés, 14 ignorés ; build weda2 vert.

**Leçons capturées** :
- mémoire `xunit-crash-affiche-passed` et Step 4 de `agents/develop.md` : un crash xUnit affiche « Passed! » ;
- `RepoScan` de Blazor aligné sur le garde d'api-mail : fichiers non suivis vus, fichiers supprimés ignorés ;
- `conventions/csharp.md` : `sortie-de-modele-non-fiable` ;
- `conventions/angular.md` : `prettier-fichier-existant` et `tiptap-commentaires-perdus` ;
- `conventions/e2e.md` : `mutation-non-servie`, variante .NET à prédicat opaque ;
- index mémoire GH_TOKEN.

**Limite connue** : sur weda2, l'intercepteur global affiche un toast pour tout 5xx. En cas de panne du fournisseur, le praticien voit ce toast en plus du message de l'aperçu. L'éviter demanderait de toucher `apps/weda2`, hors du module MSS (règle 6).

**Suite** : `/sonar task-349`.

### Refonte de la barre de rédaction Angular (demande humaine du 2026-10-01)

**Référence de design** : écran Stitch « Nouveau message - Barre d'outils optimisée »
(projet `HealthPlatform` desktop `4321689327130998790`, écran `d4226093dbf3497aa147ff367f4bdc3d`,
design system « L'Éclat Médical »). Validé par l'humain, qui a demandé de le respecter à la lettre.

- **Barre d'outils** : déplacée sous les champs À / Objet, sur un fond distinct
  (`background-muted`) ; les champs passent sur fond blanc.
  - À gauche : Joindre, puis les menus déroulants **Modèle ▾** et **Signature ▾**
    (`ds-dropdown-menu`, qui remplace les `ds-select`).
  - Au centre, après un séparateur : **Corriger l'orthographe**, avec icône, badge **IA** et
    l'infobulle « Propose des corrections sans rien modifier tant que vous ne les avez pas
    acceptées (F7) ».
  - À droite : les interrupteurs **Accusé de lecture** et « Bloquer la réponse du patient »
    (`ds-toggle`), puis la corbeille.
- **Raccourci F7** : il demande la correction quand l'action est disponible (`canCorrectSpelling`).
- **Aperçu de la correction** : une carte avec le titre « Corrections proposées (N anomalies
  détectées) », compté par `countCorrections` qui compte chaque suite de mots modifiés une fois.
  La citation est entre guillemets avec un liseré. Les actions sont **Ignorer** et **Appliquer ✓**.
- **Barre de titre** : elle affiche l'objet (sinon « Nouveau message »).
  - **Plein écran** : bascule, Échap pour sortir, réinitialisé à la fermeture.
  - **Croix ✕** : « Fermer et abandonner le brouillon », passe par la confirmation existante.
- **Tests** :
  - `mail-compose-toolbar.component.spec.ts` : 12 tests, rouges avant le code ;
  - `countCorrections` : +3 tests ;
  - mss-lib : 525/525 ;
  - build `weda2` vert ;
  - lint mss-lib : 0 erreur, 41 warnings, inchangé.
- **E2E non rejoué** : l'AppHost et le `nx serve` de l'humain occupent les ports 5052 et 4200
  (sortie 2, outillage). Il faut rejouer `/e2e` avant la PR, de toute façon nécessaire après les
  correctifs B1 à B6.
- **Signalé** : la croix et la corbeille déclenchent la même action (abandon confirmé), et la
  maquette garde les deux. L'humain tranche.

## Sonar log

Serveur SonarQube 9.9.8.100196 (`sonar.login`), new code sur 30 jours.

- **Phase 1 (new code)** : Quality Gate OK, `new_coverage` = 97,6 % (cible 95 %), **0 finding** sur le new code. Aucun correctif nécessaire : la passe qualité de `/develop` avait déjà traité S103, S125 et CA1861.
- **Phase 1, tests ajoutés** : aucun.
- **Phase 2 (legacy)** : non lancée, les cibles projet sont atteintes. Restent 8 code smells legacy.
- **Tests de la passe Release avec couverture** : 0 échec sur domain, application, infrastructure et api.
  - Integration : 4 échecs, tous des tests « aujourd'hui » de la fenêtre 22:00–24:00 UTC (analyse à 23:05 UTC), antérieurs à la task, aucun fichier de la task n'y touche.
  - Rejoués seuls : les 3 mêmes (`FilterTodayEmails…`, `GetFolderToday…`, `GetFolderNotSeenToday…`). À rejouer par `/review` après minuit UTC.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 97,6 % | 97,6 % | 0 |
| New code smells | 0 | 0 | 0 |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 8 | 8 | 0 |
| Coverage (projet) | 98,1 % | 98,1 % | 0 |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

**Conventions** : aucune règle corrigée à la main ce tour-ci. Les leçons du cycle sont consignées dans le Develop log.

## Lint log

`/lint-angular` — Mode A. Base `origin/next`, lint limité à `tag:scope:mss`, build et test sur tout le périmètre affecté. Code-only : aucune opération git hormis `git fetch origin next`.

| Mesure | Baseline | Final |
|---|---|---|
| Erreurs ESLint (scope mss) | 1 | **0** |
| Warnings (scope mss) | 88 | 88 |

- **Itération 1** (une seule a suffi) : l'unique erreur venait de la task. Il s'agit de `prettier/prettier` sur `isFeatureEnabled` dans `core/services/mss-api.service.ts`, un template literal au-delà de 100 colonnes. Je l'ai corrigée **à la main**, sans `--fix` : le scope `mss` porte du WIP humain (`mail-list.*`, `mss-mail.component.ts`, `enrichment-order.util.*`) que l'auto-fixer aurait reformaté.
- **Warnings dans les fichiers de la task** : aucun n'est introduit, sauf `max-lines` sur `ui/html-editor/html-editor.component.ts`, passé de 470 à 534 lignes par les trois méthodes de sélection. Je l'accepte, best-effort : c'est un warning, et le module tolère déjà `mss-api.service.ts` (2 370 lignes) et `mail-compose.component.ts` (1 878 lignes). Les autres warnings des fichiers touchés existaient avant la task : `jsdoc/require-example`, `max-lines`, `complexity` de `replacePlaceholders`.
- **Filet** :
  - test : ✅ `nx affected -t test`, 11 projets verts ;
  - build : ✅ 10 cibles sur 11, dont `weda2`, le consommateur de `mss-lib`.
- **Rouge préexistant sur la branche, hors task** : `mss:build:production` échoue, car le fileReplacement `apps/mss/src/environments/environment.prod.ts` n'existe pas. Le fichier n'est ni suivi, ni présent, ni ignoré depuis `7de0cee3`, donc la cible est rouge sur `feature/nova-rewriting-mss` quel que soit le code de la task.
- **Convention** : `conventions/angular.md` › `prettier-fichier-existant` passe à 2 occurrences. J'y ajoute le revers : les lignes ajoutées à un fichier existant doivent être formatées à la main.

## Lint mobile log

`/lint-mobile` — Mode A, branche `feat/task-349-correction-orthographe`. Baseline `npm run lint` : **All files pass linting** (0 erreur, 0 warning). Aucune itération nécessaire, aucun commit. Build et tests non rejoués : l'arbre n'a pas bougé depuis leur dernier vert (`/develop` §Q, 967/967).

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail, client-mobile, dtos-mss touchés | ✅ verte | 25 verts, 0 flaky, 0 rouge, 0 quarantaine | 3 min 58 s |
| angular | api-mail, client-angular, dtos-mss touchés | ✅ verte | 25 verts, 0 flaky, 0 rouge, 0 quarantaine | 3 min 18 s |

Catalogue : celui de la branche de la task (`Api/Mail/e2e/scenarios.yml`, E2E-COMPOSE-002 v1 ajouté).

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 1 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

**Flaky** : aucun. **Quarantaines** : aucune. **Divergences ouvertes** : aucune.

**Preuve du rouge (E2E-COMPOSE-002)** : j'ai muté `applySpelling` en no-op (garde opaque `Date.now() > 0`) et rejoué la voie complète, sur chaque client. Les deux voies passent ROUGE, sur l'assertion « le texte est remplacé », au premier essai puis au retry. J'ai restauré par `cp` depuis une copie, contrôlée byte à byte, puis vérifié `git status` propre sur mobile. Le verdict vert ci-dessus a été rendu avant les mutations, sur un code identique.

**Démontage** : ports 5052/8100/4200/3993/3465/3143 libres, aucun conteneur `e2e-dovecot-*` ni `e2e-greenmail-*` résiduel.

**Parcours touché sans spec modifié** : aucun avertissement. `mail-compose.component.html` est modifié sur les deux clients, et `live-ai` aussi.

## Review log

**/review du 2026-10-01 : CHANGES REQUESTED.** Builds et tests verts sur les 5 repos, E2E vert. Six points bloquants détaillés dans `questions/task-349.md` (B1 garde à sens unique, B2 signature Angular, B3-B5 Blazor, B6 sélection multi-blocs). Aucun commit, aucune PR ; chaîne arrêtée.

## Timings

*(généré par `tools/timing/report.sh --task task-349 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 29 s | — | — | — | — |
| /develop | ok | 1 h 17 min | 12 (2 min 00 s) | 21 (10 min 22 s) | — | dtos-mss 1B/0T, api-mail 3B/9T, client-blazor 4B/7T, client-angular 2B/2T, client-mobile 2B/3T |
| /sonar | ok | 9 min 15 s | 1 (17 s) | 5 (5 min 01 s) | 2 (38 s) | 1 itération(s), api-mail 1B/5T |
| /lint-angular | ok | 5 min 34 s | 1 (21 s) | 1 (54 s) | — | 1 itération(s), client-angular 1B/1T |
| /lint-mobile | ok | 22 s | — | — | — | baseline propre |
| /e2e | ok | 6 h 48 min | — | — | — | e2e ×5 (14 min 18 s), 2 voies vertes 25/25, parité verte, mutation COMPOSE-002 rouge x2 |
| /review | failed | 10 min 41 s | 5 (42 s) | 4 (3 min 41 s) | — | dtos-mss 1B/0T, api-mail 1B/1T, client-mobile 1B/1T, client-blazor 1B/1T, client-angular 1B/1T, code review CHANGES REQUESTED : 6 bloquants (garde 1 sens, signature Angular, Blazor x3, multi-blocs) |
| **Total cycle** | | **8 h 32 min** | **19 (3 min 22 s)** | **31 (19 min 59 s)** | **2 (38 s)** | |

Autres commandes mesurées : lint ×3 (48 s), nuget-wait ×1 (19 s), restore ×2 (26 s)

## Stitch design log

- Project : client-mobile (id 10088502293310567548)
- Screens :
  | Component / Page | Stitch title | Screen id | Action | Screenshot |
  |---|---|---|---|---|
  | mail-compose | mail-compose | 57f1304fa14f449f90e914d1130779ed | reused | https://lh3.googleusercontent.com/aida/AEtjO1VxTzbj9CurbTmNDGYUMloAEn7zw1JosBEqRk7-KT5WHjWHipZzTZjk3_DRUlBpD1TxUeRg_aJkh1Id2U2jHD2ZXxl133QLYznp-h4xoRrtpAnpvDRiegrmizLrWCzdK69PSjm-eyboQTHwAiVqhrsLB_dTod4UzPll1DP3-qP6lIxX9daZeoh4sjmehWblcJ3V4Ow_RFnbLPZHk8LnCN_BPd_E1muzbaXcqaHhfSANyF3b3vJpRIPDGxw |
- Le panneau d'aperçu de la correction n'existe pas encore dans Stitch. Aucune génération n'a été lancée : c'est un ajout mineur à un écran existant. Il suit le design system « Clinical Precision » : bannière intégrée « Surface Alt », bouton primaire plein « Appliquer », bouton secondaire à contour « Annuler », cible de 44 px, texte retiré en rouge atténué, texte ajouté en vert.
- ⚠ Rename / labelliser in Stitch UI : aucun libellé d'instance `mail-compose` ; deux écrans portent ce titre.
- ⚠ Doublons suspectés à nettoyer dans l'UI : `340f18be9395435f8fc472e0c476f736` et `57f1304fa14f449f90e914d1130779ed`, tous deux titrés `mail-compose` ; le second, plus récent, sert de référence.
- Stitch reachable : ✓
