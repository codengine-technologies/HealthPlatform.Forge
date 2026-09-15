# todo-task-309.md — La gestion des messageries devient atteignable : monter le sélecteur là où il manque, et le rendre trouvable

**Repos**: client-angular, client-blazor, client-mobile
**Dependencies**: **task-304** (mergée le 2026-09-14 — elle a livré le sélecteur et l'écran
de gestion sur les trois fronts), **task-308** (PRs ouvertes — elle a fait du rattachement
le seul chemin d'obtention d'une boîte, ce qui rend ce défaut bloquant). Aucune dépendance
sortante.
**Epic**: E016
**Priorité**: **1** — un praticien qui a rattaché sa première messagerie ne peut pas en
ajouter une seconde. La fonctionnalité multi-messageries, livrée et mergée, est
**inatteignable** pour lui.

## Objective

Rendre la gestion des messageries atteignable depuis l'interface, sur les trois fronts, et
la rendre **trouvable** sans exploration.

Cette US n'écrit presque aucune fonctionnalité : tout existe. Elle branche une pièce
oubliée, ajoute un point d'entrée visible, et couvre par des tests un composant qui n'en a
aucun.

## Le constat, et ce qu'il a fallu chercher pour le comprendre

**Constat humain du 2026-09-14**, après le premier rattachement réel sur `client-angular` :
*« après avoir rattaché une première messagerie, je m'attends à pouvoir en ajouter une
nouvelle ; cette option n'est pas disponible dans l'interface. »*

La lecture naïve serait « la gestion multi-messageries n'est pas faite ». Elle est fausse.
Vérification faite, **tout existe** :

| Pièce | État sur `client-angular` |
|---|---|
| `mss-mailbox-switcher` | **écrit et complet** — avatar, identité du praticien, liste des boîtes, bascule en direct (`session.switchTo`), boutons « Ajouter une messagerie » et « Gérer mes messageries » |
| `mailbox-management` | **écrit** — liste, pastilles par défaut / courante, définir par défaut, ré-essayer l'authentification, supprimer, formulaire d'ajout |
| Route `accounts` | **déclarée** — `/messagerie/accounts` répond |

**Et pourtant rien n'y mène.** Aucun template du dépôt ne contient
`<mss-mailbox-switcher>` : le composant est exporté par `libs/mss/src/ui/index.ts` et
**monté nulle part**. Le seul chemin vers la gestion est de taper l'URL à la main.

### Le défaut est sur un seul front

| Front | Sélecteur écrit | **Monté** | Où |
|---|---|---|---|
| `client-angular` | ✅ | ❌ **nulle part** | — |
| `client-blazor` | ✅ | ✅ | `Mail.razor:50` |
| `client-mobile` | ✅ | ✅ | `inbox.page.html:120` |

task-304 a livré la pièce sur les trois fronts et ne l'a branchée que sur deux. C'est une
ligne de template manquante, pas une fonctionnalité absente — mais du point de vue du
praticien, la différence est nulle : la fonctionnalité n'existe pas.

> **Pourquoi ce défaut devient bloquant maintenant.** Tant que le registre se remplissait
> tout seul, un praticien n'avait qu'une boîte et ne cherchait pas à en ajouter. Depuis
> task-308, rattacher est le **seul** moyen d'obtenir une messagerie — et le parcours
> s'arrête après la première.

## Décisions de PO — arbitrage humain du 2026-09-14

**1. Emplacement : la page Messagerie, et elle seule.** Le sélecteur se monte là où Blazor
et Mobile le montent déjà. Un praticien qui passe d'un front à l'autre retrouve le même
geste au même endroit.

**2. Une entrée de navigation « Mes messageries » dans la sidebar Angular, EN PLUS.**

> ⚠️ **Asymétrie délibérée — c'est le point à contester si vous n'êtes pas d'accord.**
> Elle diverge de la parité stricte retenue au point 1, et elle est assumée : **seul
> Angular a une barre de navigation latérale**. Blazor et Mobile n'ont pas de surface
> équivalente où poser cette entrée — sur Mobile le sélecteur vit sur la page d'accueil,
> donc il est vu ; sur Blazor il est sur la page qu'on ouvre en premier.
>
> Sur Angular, le sélecteur est derrière un clic sur un avatar. **C'est précisément ce
> défaut de découvrabilité qui a produit le constat**, et le corriger en montant
> simplement le sélecteur laisserait la gestion aussi discrète qu'avant. Deux chemins vers
> le même écran est ici le comportement voulu : un rapide (l'avatar, depuis la
> messagerie), un explicite (la navigation, depuis n'importe où).

**2 bis. Où exactement — validé le 2026-09-14.** L'entrée se place en **avant-dernière
position, juste avant « Paramètres »** :

```
🏠  Tableau de bord        │
✉️  Messagerie             │  usage quotidien
👥  Contacts               │
📄  Modèles                │
👤  Patient                │
───────────────────────────
📄  Journal d'audit        │  consultation / configuration
📬  Mes messageries   ← NOUVEAU (route `accounts`)
⚙️  Paramètres             │
```

- **Libellé** : « Mes messageries ». Le possessif dit qu'il s'agit du compte du praticien,
  pas d'une boîte partagée.
- **Icône** : `communication` / `mail-02` — déjà employée dans le dépôt (`mail-widget`) et
  **distincte** de `communication/mail`, qui porte « Messagerie ». Deux icônes de la même
  famille, deux formes différentes : la parenté se lit, la confusion est évitée.
- **Pourquoi pas en position 3, sous « Messagerie »** : l'adjacence thématique serait plus
  forte, mais elle casserait le bloc d'usage quotidien avec une entrée qu'on ouvre trois
  fois par an.
- **Pourquoi « Paramètres » reste dernier** : c'est une convention que les praticiens ont
  intégrée dans tous leurs logiciels. La déplacer coûterait plus que le gain d'adjacence.

> **L'alternative écartée, et pourquoi.** L'écran **Paramètres** porte déjà quatre sections
> (`Identité de l'expéditeur`, `Lecture`, `Organisation`, `Avancé`), et la gestion des
> messageries y aurait sa place — « Identité de l'expéditeur » parle de la même chose.
> Écartée **parce qu'elle enfouit la gestion d'un cran de plus**, alors que le défaut qu'on
> corrige est précisément qu'elle était introuvable. Une entrée de premier niveau est
> visible depuis n'importe quel écran ; une section dans Paramètres demande d'ouvrir
> Paramètres puis de faire défiler.

**3. Périmètre : les trois fronts.** Angular reçoit le montage ; Blazor et Mobile sont
**vérifiés** — le parcours y est-il réellement complet de bout en bout ? Aucun des trois
sélecteurs n'a de test aujourd'hui, sur aucun front : c'est ce qui a permis à un composant
non monté de passer une revue et un merge.

**4. Le sélecteur Angular passe au design system.** Il est en HTML brut (`<button>`,
`<ul>`, styles maison) — exactement l'état dans lequel étaient les cinq écrans de
rattachement avant leur conversion du 2026-09-14. Le monter tel quel afficherait à l'écran
ce qui vient d'être corrigé juste à côté.

## Contrainte technique connue

**La page Messagerie d'Angular n'a aucun en-tête.** `mss-mail.component.html` est un
`folder-panel` + un `content-panel`, sans bandeau supérieur — là où Blazor et Mobile en ont
un. La zone qui accueillera le sélecteur est donc à créer, et elle ne doit pas manger la
hauteur utile de la liste de messages.

## Definition of Done

### `client-angular` — le montage et la découvrabilité

- [ ] `npm ci && npm run build` passe (0 erreur) ; `npm test` passe (0 échec)
- [ ] `<mss-mailbox-switcher />` est monté sur la page Messagerie, dans une zone d'en-tête
      créée pour lui. **Vérification binaire** : `grep -rn "mss-mailbox-switcher" libs/mss/src --include=*.html` rend au moins un montage hors du composant lui-même
- [ ] Une entrée **« Mes messageries »** est ajoutée à `NAV_ITEMS`
      (`mss-layout.component.ts`), **en avant-dernière position, juste avant
      « Paramètres »**, `path: 'accounts'`, `iconCategory: 'communication'`,
      `iconName: 'mail-02'`. L'ordre des sept entrées existantes est **inchangé**
- [ ] **En sidebar repliée**, « Messagerie » (`mail`) et « Mes messageries » (`mail-02`)
      restent distinguables à l'icône seule — c'est le seul état où la parenté des deux
      icônes peut se retourner en confusion. Vérifié à l'œil, consigné dans le task file
- [ ] Depuis la messagerie, l'avatar ouvre le menu, et « Ajouter une messagerie » comme
      « Gérer mes messageries » mènent à l'écran de gestion
- [ ] Le sélecteur est converti au **design system** : `ds-button`, `ds-card` (ou
      équivalent pour le menu), `ds-icon`. **Tous les `data-testid` sont conservés à
      l'identique**
- [ ] L'en-tête ajouté ne réduit pas la hauteur utile de la liste de messages de plus de
      ce que le sélecteur occupe réellement — vérifié à l'œil sur un écran 1080p

### Les trois sélecteurs — la couverture qui manquait

- [ ] **`client-angular`** — `mailbox-switcher.component.spec.ts` (nouveau) : le menu
      s'ouvre et se referme ; la liste rend une entrée par boîte ; choisir une autre boîte
      appelle `session.switchTo` ; « Ajouter » et « Gérer » naviguent vers `accounts` ;
      **hors ligne, « Ajouter » est grisé** et porte son libellé d'explication
- [ ] **`client-mobile`** — spec équivalent sur `mailbox-switcher.component`
- [ ] **`client-blazor`** — test bUnit équivalent sur `MailboxSwitcher.razor`
- [ ] **La contre-épreuve du défaut de cette US** : sur chaque front, un test échoue si le
      sélecteur cesse d'être monté sur la page qui doit le porter. Sans lui, cette US
      pourrait se reproduire à l'identique
- [ ] Les trois suites restent vertes : Blazor (`dotnet test HealthPlatform.Client.sln`),
      Mobile (`npm test -- --watch=false --browsers=ChromeHeadless`), Angular (`npm test`)

### Vérification de parité — Blazor et Mobile

- [ ] Sur `client-blazor` et `client-mobile`, le parcours est **parcouru et constaté** :
      depuis la messagerie, ouvrir le sélecteur, ajouter une seconde boîte, basculer
      dessus, revenir. Tout écart avec Angular est **consigné dans le task file**, et
      corrigé s'il tient en moins d'un écran de code — sinon il ouvre une US dédiée
- [ ] **Aucun changement de comportement** sur Blazor et Mobile : le diff s'y limite aux
      fichiers de test, sauf écart de parité explicitement consigné et justifié

## Manual Test Plan

- **Lancer** : `cd Api/Mail && aspire run --project src/AppHost`, puis le front :
  - Angular : `cd Client/Angular/front && npx nx serve weda2` → `/messagerie`
  - Blazor : `cd Client/Blazor && dotnet run --project src/Shell` → `/Mail`
  - Mobile : `cd Client/Mobile && npm start` → onglet Messagerie
- **Actions et vérifications, sur chacun des trois fronts** :
  1. Se connecter avec un praticien ayant **une seule** messagerie rattachée.
  2. Ouvrir la messagerie. **Attendu : le sélecteur est visible** — avatar, adresse
     courante.
  3. Cliquer l'avatar → le menu s'ouvre, liste la messagerie courante, et propose
     **« Ajouter une messagerie »** et **« Gérer mes messageries »**.
  4. Cliquer « Ajouter » → l'écran de gestion s'ouvre, avec son formulaire de
     rattachement.
  5. Rattacher une **seconde** messagerie MSSanté de formation → **201**, elle apparaît
     dans la liste.
  6. Rouvrir le sélecteur → **les deux messageries sont listées**, la courante est
     marquée.
  7. Choisir la seconde → la bascule s'opère, l'interface se fige brièvement, et la boîte
     de réception se recharge sur la nouvelle messagerie.
  8. **Le test qui prouve l'US** : à aucun moment il n'a fallu taper une URL.
- **Spécifique Angular** :
  9. Depuis **Contacts** (donc hors messagerie), cliquer **« Mes messageries »** dans la
     barre latérale → l'écran de gestion s'ouvre. Vérifier au passage qu'elle est bien
     **juste au-dessus de « Paramètres »**, et que l'ordre des autres entrées n'a pas
     bougé.
  9 bis. Replier la sidebar (chevron en haut) → **« Messagerie » et « Mes messageries »
     restent distinguables** à l'icône seule.
- **Hors ligne** (sans session Pro Santé Connect) :
  10. Ouvrir le sélecteur → **« Ajouter une messagerie » est grisé**, avec l'explication
      « Connexion Pro Santé Connect requise », et les boîtes déjà rattachées restent
      listées et ouvrables en lecture.
- **Données de test** : praticien synthétique du realm de formation, deux adresses MSSanté
  de formation. Aucune donnée de santé réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — accessibilité d'une fonctionnalité déjà livrée, aucun
  flux nouveau
- **Exigences DSR honorées** : non applicable — cette US n'ajoute aucun échange ni aucun
  document ; elle rend atteignable un écran existant
- **INS** : non applicable — aucun patient manipulé. Le parcours porte sur les messageries
  du praticien, jamais sur une identité patient
- **Authentification PS** : **inchangée, et c'est un point de vigilance**. Le rattachement
  d'une messagerie exige une session **Pro Santé Connect** active (eIDAS substantiel) et
  une sonde XOAUTH2 validée par l'opérateur MSSanté — garanties côté serveur par
  `MailboxManagementService.AttachAsync`. Cette US ne les touche pas et ne doit pas les
  contourner : **le bouton « Ajouter » est grisé hors ligne**, il n'ouvre pas un formulaire
  qui échouerait
- **Habilitations** : inchangées. Aucune route nouvelle, aucun contrôle d'accès modifié.
  L'entrée de navigation ajoutée pointe sur une route déjà déclarée et déjà gardée
- **Interop CI-SIS** : non applicable — aucun échange de document
- **Tracé PGSSI-S** : inchangé. La bascule de messagerie est déjà journalisée côté serveur
  (`MailboxSessionOpened`, à la frontière de session), le rattachement aussi
  (`MailboxAttached`). Cette US ne crée aucun évènement et n'en supprime aucun. **Aucune
  adresse MSSanté ne doit apparaître dans un journal front**
- **Consentement patient** : non applicable — aucune donnée patient
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — aucun flux, aucune donnée déplacée
- **AIPD / impact RGPD** : **inchangé**. Aucune donnée personnelle nouvelle n'est collectée,
  affichée ou transmise. Les adresses MSSanté et l'identité du praticien affichées par le
  sélecteur le sont déjà par les écrans existants

### DOD santé applicable

- [ ] Aucune donnée de santé en clair dans les logs front (aucune adresse MSSanté, aucun
      RPPS journalisé par les composants touchés)
- [ ] Le bouton « Ajouter une messagerie » est **inopérant sans session PSC** sur les trois
      fronts — vérifié par test, pas seulement à l'œil

## Ce que cette US n'est pas

- **Pas une US de fonctionnalité.** Le sélecteur, la bascule, l'écran de gestion, le
  formulaire d'ajout et la route existent tous et sont mergés. Si le diff commence à
  ajouter du comportement, c'est qu'il déborde.
- **Pas une refonte de la navigation Angular.** Une entrée s'ajoute à `NAV_ITEMS`, en
  avant-dernière position ; la structure de la barre latérale, son repli, et **l'ordre des
  sept entrées existantes** ne bougent pas.
- **Pas un déplacement de la gestion dans « Paramètres ».** L'alternative a été examinée et
  écartée le 2026-09-14 — elle enfouirait la gestion d'un cran de plus, à rebours du défaut
  corrigé.
- **Pas une harmonisation des trois navigations.** L'entrée « Mes messageries » est
  **Angular seulement**, faute de surface équivalente ailleurs — décision assumée, encadrée
  ci-dessus, et contestable.
- **Pas la passe design system des deux autres fronts.** Blazor et Mobile ont leurs propres
  systèmes visuels (Radzen, Ionic) ; seul le sélecteur Angular est converti, par cohérence
  avec les cinq écrans de rattachement traités la veille.

## Branches

- `client-blazor` (pushed) : `fix/task-309-selecteur-messageries-atteignable` — https://github.com/codengine-technologies/HealthPlatform.Client/tree/fix/task-309-selecteur-messageries-atteignable
- `client-mobile` (pushed) : `fix/task-309-selecteur-messageries-atteignable` — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-309-selecteur-messageries-atteignable
- `dtos-mss` (pushed, auto-inclus) : `fix/task-309-selecteur-messageries-atteignable` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-309-selecteur-messageries-atteignable
- `client-angular` (code-only) : la forge écrit sur la branche actuellement checked out dans `Client/Angular/` — **`feature/nova-rewriting-mss`** à l'heure du `/start` ; l'humain gère branche, commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-309 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 1 min 23 s | — | — | — | — |
| /develop | ok | 26 min 54 s | 3 (1 min 53 s) | 4 (2 min 35 s) | — | client-angular 2B/1T, client-mobile 0B/2T, client-blazor 1B/1T |
| /lint-angular | ok | 2 min 55 s | — | — | — | — |
| /lint-mobile | ok | 55 s | — | — | — | — |
| /verify-visual | skipped | 31 s | — | — | — | diff client-mobile non visuel : 2 specs, 1 methode, 1 liaison de clic |
| /review | ok | 7 min 14 s | 3 (1 min 58 s) | 3 (1 min 57 s) | — | client-blazor 0B/1T, client-mobile 1B/1T, dtos-mss 1B/0T, client-angular 1B/1T |
| /tech-writer | ok | 4 min 10 s | — | — | — | — |
| **Total cycle** | | **44 min 05 s** | **6 (3 min 51 s)** | **7 (4 min 32 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×2 (1 min 50 s)

## Develop log

**Rien de fonctionnel n'a été écrit** — conformément à l'US. Une pièce oubliée
est branchée, un point d'entrée est ajouté, un composant sans aucun test en
reçoit vingt-trois, et une règle qui ne tenait qu'à un attribut de rendu passe
dans le code.

### `client-angular` (code-only — non commité)

| Fichier | Ce qui change |
|---|---|
| `features/mail/mss-mail.component.html` / `.scss` / `.ts` | **L'en-tête de la messagerie**, qui n'existait pas, et le montage de `<mss-mailbox-switcher />` dedans |
| `features/layout/mss-layout.component.ts` | Entrée **« Mes messageries »** dans `NAV_ITEMS`, avant-dernière, `accounts` / `communication` / `mail-02` |
| `ui/mailbox-switcher/*` | Conversion **design system** (`ds-button`, `ds-card`, `ds-icon`) — tous les `data-testid` à l'identique — et la garde hors ligne |

**La coquille était le vrai obstacle.** `mss-mail.component.html` n'avait aucune
surface d'en-tête : deux panneaux et rien d'autre, là où Blazor et Mobile en
avaient un. C'est cette absence qui explique qu'on ait pu livrer le sélecteur
sans jamais le monter — il n'y avait nulle part où le poser. La page devient
`.mail-shell` (colonne) = `.mail-header` (hauteur minimale) + `.mail-container`
(`flex: 1` + `min-height: 0`, sans quoi la liste déborderait au lieu de défiler).

**Un échec de build instructif** : `justify="start"` sur `ds-button` —
`ButtonJustify` n'admet que `center | space-between`. Retiré.

### `client-mobile` (poussé) et `client-blazor` (poussé)

Diff limité aux tests, **plus une ligne de comportement** consignée ci-dessous.

### Les tests qui manquaient — 23 au total

| Front | Fichier | Tests |
|---|---|---|
| angular | `mailbox-switcher.component.spec.ts` | 8 |
| angular | `mss-layout.component.spec.ts` | 4 (ordre des entrées, position, icônes distinctes, lien rendu) |
| angular | `mss-mail.component.mount.spec.ts` | 2 — **contre-épreuve** |
| mobile | `mailbox-switcher.component.spec.ts` | 8 |
| mobile | `inbox.page.mount.spec.ts` | 1 — **contre-épreuve** |
| blazor | `MailboxSwitcherComponentTests.cs` | 7 |
| blazor | `MailboxSwitcherMountGuardTests.cs` | 1 — **contre-épreuve** |

**Trois contre-épreuves, deux techniques, et c'est l'outil qui décide.** La
question posée est la même partout — *la page monte-t-elle le sélecteur ?* —
mais Vitest et xUnit lisent le disque (le source de la page fait foi, et le
compilateur couvre l'autre moitié : un élément inconnu casse le build), tandis
que Karma tourne dans un navigateur sans accès fichier : côté mobile, la page
est donc **rendue superficiellement** (`NO_ERRORS_SCHEMA`), ce qui laisse la
balise dans le DOM sans instancier la liste de mails ni ses dépendances.

### Le défaut trouvé par le test — et pourquoi il est dans le code, pas dans le rendu

Le test « hors ligne, "Ajouter" ne navigue pas » a échoué **au premier coup**
côté Angular : le clic sur un `ds-button` désactivé déclenchait quand même le
gestionnaire du parent. L'inopérance ne tenait donc qu'au **rendu** (le
`<button disabled>` interne, qui protège un vrai clic de souris mais pas un
événement reçu par l'hôte).

Ce n'est **pas** un bug utilisateur démontré — il faudrait un chemin de clic
atteignant l'hôte. C'est une **règle métier qui vivait dans une feuille de
style** : « rattacher exige une session Pro Santé Connect » appartient à
l'écran. Une méthode `addMailbox()` la porte désormais sur les **trois** fronts,
ce qui la rend vraie quel que soit le chemin du clic et **vérifiable par un
test**, comme la DOD santé l'exige. « Gérer » reste ouvert hors ligne :
consulter ce qu'on possède déjà n'exige aucun jeton.

### Vérification de parité — deux écarts relevés

1. **Garde hors ligne absente des trois fronts** — *corrigée* (ci-dessus), une
   méthode par front.
2. **Destination après bascule — non corrigée, arbitrage PO requis.** Angular
   route vers `dashboard` (le tableau de bord), Blazor vers `/Mail` et Mobile
   vers `/tabs/messages` (la boîte de réception). Le commentaire du code Angular
   annonce pourtant « la nouvelle boîte s'ouvre sur sa boîte de réception » :
   **le code et son commentaire divergent sur le front de référence**. Un mot
   suffirait à aligner, mais lequel des deux comportements est le bon est une
   décision produit, pas une simplification — laissé au HAG.

Le reste des différences est idiomatique et non un écart : menu déroulant ancré
(Angular/Blazor) contre feuille `ion-modal` (Mobile), et l'entrée de navigation
« Mes messageries » qui est **Angular seulement** par décision de PO — les deux
autres fronts n'ont pas de surface équivalente.

### Passe qualité (`/simplify`, intégrée)

Diff court et fraîchement écrit ; **un seul nettoyage appliqué** : la spec
Angular contenait un test qui réinitialisait le `TestBed` **en son milieu** pour
exercer deux boutons — scindé en deux tests, chacun avec son montage.
Re-validation : suite `mss-lib` **361 verts** (la scission ajoute le 361e).
Build applicatif non rejoué pour ce seul nettoyage : les specs sont hors du
bundle. `dtos-mss` — porteur de contrat, jamais de passe qualité ; aucun commit
non plus, la task ne touche aucun DTO.

### Vérifications

| Repo | Build | Tests |
|---|---|---|
| `client-angular` | `nx build weda2` — **0 erreur** | `nx test mss-lib` — **361 verts** |
| `client-mobile` | `npm run build` (hook pre-push) — **0 erreur** | **832 verts**, 0 échec |
| `client-blazor` | `dotnet build HealthPlatform.Client.sln` — **0 erreur** | **240 verts**, 2 ignorés, 0 échec |

**Vérification binaire de la DOD** :
`grep -rn "mss-mailbox-switcher" libs/mss/src --include=*.html` rend un montage
réel (`mss-mail.component.html:15`), hors du composant lui-même.

### État git

- `client-blazor` : commit `80d4e1e`, **poussé**.
- `client-mobile` : commit `7dbab49`, **poussé**.
- `dtos-mss` : branche créée par `/start`, **aucun commit** — aucun contrat touché.
- `client-angular` : **10 fichiers non commités** (7 modifiés, 3 nouveaux) sur
  `feature/nova-rewriting-mss` — mode code-only, l'humain commit et pousse vers
  TFS. Les deux `environments/environment.ts` modifiés **préexistaient** à la
  task : ne pas les confondre avec son diff.

### Reporté au test humain (HAG)

Deux critères de la DOD sont des observations à l'œil, pas des assertions : la
distinction des icônes `mail` / `mail-02` **en sidebar repliée**, et le fait que
l'en-tête ajouté ne mange pas la hauteur utile de la liste sur un écran 1080p.
Le test « les deux icônes diffèrent » est automatisé ; « elles se distinguent
à l'œil » ne l'est pas.

## Lint log

**Zéro erreur ESLint dès la ligne de base — aucune itération consommée** (0 / 5).

Commande, alignée sur le Stage 2 du pipeline Azure :

```bash
npx nx affected -t lint --base=origin/next --head=HEAD --parallel=3 --projects=tag:scope:mss
```

11 projets lintés, `origin/next` à `c1f0ad90`.

| Projet | Erreurs | Avertissements |
|---|---|---|
| `mss` (app) | 0 | 0 |
| `mss-lib` | **0** | 41 |
| `weda2` | 0 | 14 |
| `dmp-lib` | 0 | 1 |
| `design-system`, `prescription*`, `ins*`, `shared`, `dmp` | 0 | 0 |

**Les 56 avertissements sont préexistants et hors diff** : `max-lines` sur des
fichiers longs de longue date, `jsdoc/require-example` sur des méthodes écrites
avant ce cycle, et deux `complexity` dans des services que la task ne touche
pas. Le seul fichier du diff qui apparaît, `mss-mail.component.ts`, y figure
pour un `max-lines` à 675 lignes — la task lui en ajoute **deux** (un import et
une entrée dans `imports:`). Le réduire serait un refactor hors charte, sans
rapport avec l'US.

**Ce que ce zéro dit du cycle.** `conventions/angular.md` a été lu avant
d'écrire, et ses trois consignes actives ont été appliquées d'emblée : control
flow natif (`@if` / `@for`) dans l'en-tête et le menu, préfixe `mss-` sur les
sélecteurs, et surtout **JSDoc complet écrit en même temps que la méthode** sur
`addMailbox()` — la règle qui avait coûté 23 squelettes creux à task-304 et deux
`require-param` à task-308. Aucune récidive : **aucune entrée à incrémenter
dans `conventions/angular.md`**, le protocole ne se déclenchant que sur une
correction manuelle.

Code-only : aucune opération git sur `client-angular`. La seule commande git de
l'étape est le `git fetch origin next` qui rafraîchit la référence de
comparaison, comme le pipeline le fait avant son propre lint.

## Lint mobile log

**`All files pass linting.` dès la ligne de base — aucune itération consommée**
(0 / 5), sur la branche `fix/task-309-selecteur-messageries-atteignable`.

```bash
cd Client/Mobile && npm run lint      # ng lint, projet "app"
```

**0 erreur, 0 avertissement.** Contrairement à `client-angular`, la
configuration ESLint de `client-mobile` ne porte ni `jsdoc/require-*` ni
`max-lines` : il n'y a donc pas même de bruit préexistant à écarter.

**Aucun commit, aucun push** : l'automation git de cette étape ne s'exerce que
sur des correctifs, et il n'y en a aucun. Le code mobile de la task est déjà
poussé par `/develop` (commit `7dbab49`).

**Aucune entrée à incrémenter dans `conventions/angular.md`** : le protocole ne
se déclenche que sur une correction manuelle, et il n'y en a pas eu. Les deux
specs mobiles écrites par ce cycle passent le lint telles qu'écrites — control
flow natif, préfixe `app-`, `data-testid` sur les éléments interactifs.

## Visual verify log

**Skip propre — aucun écran mobile touché.**

Le diff `client-mobile` de la task est entièrement non visuel :

| Fichier | Nature |
|---|---|
| `inbox.page.mount.spec.ts` (+87) | test |
| `mailbox-switcher.component.spec.ts` (+159) | test |
| `mailbox-switcher.component.ts` (+20) | une méthode `addMailbox()` |
| `mailbox-switcher.component.html` (1 ligne) | `(click)="goToManagement()"` devient `(click)="addMailbox()"` |

**Le rendu est identique au caractère près** : même arborescence, mêmes
libellés, mêmes `data-testid`, même état `disabled`. Seule la cible d'un
gestionnaire de clic change. Aucun écran de `screens.json` n'est donc à
recapturer, et l'état visuel global de l'application
(`Docs/epics/img/screens/client-mobile/`) reste à jour.

**Ce que ce skip ne couvre pas, et pourquoi c'est acceptable** : le critère
bloquant de cette étape est l'écran blanc ou le crash de navigation. Le seul
chemin par lequel ce diff pourrait en produire un serait une liaison de
template invalide — ce que le `ng build` de `/develop` (0 erreur) et les 832
tests verts, dont le rendu superficiel de la page Messages, excluent déjà.

Le parcours visuel mobile complet — ouvrir le sélecteur, ajouter une seconde
boîte, basculer — reste au **plan de test manuel** (HAG), où il est décrit
écran par écran.

## PRs

- `client-blazor` (pushed) : **[PR #76](https://github.com/codengine-technologies/HealthPlatform.Client/pull/76)** — label `awaiting-human-merge`
- `client-mobile` (pushed) : **[PR #72](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/72)** — label `awaiting-human-merge`
- `dtos-mss` (auto-inclus) : branche créée par `/start`, **aucun commit** — la
  task ne touche aucun contrat DTO. Pas de PR ; la branche vide est nettoyée au
  `/merge`.
- `client-angular` (**code-only**) : l'humain gère commit / push TFS et
  l'ouverture de la PR. **10 fichiers** à relire dans WindSurf, non commités sur
  `feature/nova-rewriting-mss` :

  | Fichier | État |
  |---|---|
  | `libs/mss/src/features/layout/mss-layout.component.ts` | modifié |
  | `libs/mss/src/features/layout/mss-layout.component.spec.ts` | **nouveau** |
  | `libs/mss/src/features/mail/mss-mail.component.html` | modifié |
  | `libs/mss/src/features/mail/mss-mail.component.scss` | modifié |
  | `libs/mss/src/features/mail/mss-mail.component.ts` | modifié |
  | `libs/mss/src/features/mail/mss-mail.component.mount.spec.ts` | **nouveau** |
  | `libs/mss/src/ui/mailbox-switcher/mailbox-switcher.component.html` | modifié |
  | `libs/mss/src/ui/mailbox-switcher/mailbox-switcher.component.scss` | modifié |
  | `libs/mss/src/ui/mailbox-switcher/mailbox-switcher.component.ts` | modifié |
  | `libs/mss/src/ui/mailbox-switcher/mailbox-switcher.component.spec.ts` | **nouveau** |

  ⚠️ Les deux `apps/*/src/environments/environment.ts` modifiés dans le même
  arbre **préexistaient** à la task — ne pas les inclure dans son commit.

## Code Review Summary

**APPROVED** — 17 fichiers relus sur trois fronts, **0 blocage**, 2 suggestions
non bloquantes et 1 arbitrage laissé à l'humain.

### Ce que la revue confirme

- **Le diff ne déborde pas.** L'US annonçait « presque aucune fonctionnalité » :
  hors tests, le diff se réduit à un en-tête de page, une entrée de navigation,
  un habillage design system à `data-testid` constants, et une méthode de garde
  par front. Aucun comportement nouveau, aucune route nouvelle, aucun contrôle
  d'accès touché.
- **Aucun reste** : ni `TODO`, ni `console.log`, ni test focalisé (`it.only` /
  `fdescribe`), ni code mort dans les trois diffs.
- **Santé / sécurité** : aucune adresse MSSanté réelle, aucun RPPS réel, aucun
  identifiant dans les fixtures (`box-1@mssante.fr`, RPPS `90000000001`). Aucun
  journal front n'émet d'adresse. Le chemin de rattachement reste derrière Pro
  Santé Connect — et l'est désormais **par le code**, pas seulement par un
  attribut de rendu.
- **Les tests sont signifiants** : chacun échouerait si le comportement
  disparaissait. Les trois contre-épreuves de montage échouent si la page cesse
  de porter le sélecteur — c'est la seule classe de défaut que ce cycle existe
  pour empêcher de se reproduire.

### Suggestions non bloquantes

1. **`aria-expanded` a changé de porteur (Angular).** Il était sur le `<button>`
   natif ; il est désormais sur l'hôte `ds-button`, donc **pas sur l'élément
   focusable**. Un lecteur d'écran annoncera le bouton sans son état déplié.
   Corriger proprement demande une entrée `ariaExpanded` côté design system —
   hors charte de cette task, et hors du module MSS.
2. **`mss-mail.component.ts` dépasse `max-lines` (675 / 500)**, avertissement
   préexistant que la task n'aggrave que de deux lignes. Le découper est un
   refactor à part entière.

### Arbitrage laissé à l'humain (non bloquant)

**La destination après bascule diverge entre les trois fronts** : Angular route
vers `dashboard`, Blazor vers `/Mail`, Mobile vers `/tabs/messages`. Le
commentaire du code Angular — le front de référence de l'US — annonce pourtant
« la nouvelle boîte s'ouvre sur sa boîte de réception ». **Le code et son
commentaire divergent.** Un mot suffit à aligner, mais lequel des deux
comportements est le bon est une décision produit, pas une simplification :
laissé au HAG.

### Vérifications rejouées par `/review`

| Repo | Build | Tests |
|---|---|---|
| `client-angular` | `nx build weda2` — **0 erreur** | `nx test mss-lib` — **361 verts** |
| `client-mobile` | `npm run build` — **0 erreur** | **832 verts**, 0 échec |
| `client-blazor` | (build implicite) | **240 verts**, 2 ignorés, 0 échec |
| `dtos-mss` | `dotnet build` — **0 erreur** | n/a |

### DOD — état

Tous les critères commandables sont vérifiés (build, tests, montage, entrée de
navigation et sa position, conversion design system à `data-testid` constants,
23 tests neufs dont 3 contre-épreuves, refus hors ligne testé sur les trois
fronts). **Deux critères restent des observations à l'œil**, reportés au plan de
test manuel : la distinction des icônes `mail` / `mail-02` **en sidebar
repliée**, et le fait que l'en-tête ajouté ne mange pas la hauteur utile de la
liste sur un écran 1080p.

## Merged

**Date** : 2026-09-15 — `/merge 309 --i-tested`

| Repo | PR | Commit squash sur `develop` |
|---|---|---|
| `client-blazor` | [#76](https://github.com/codengine-technologies/HealthPlatform.Client/pull/76) | `5733722` |
| `client-mobile` | [#72](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/72) | `f10e1bc` |
| `dtos-mss` | aucune (branche auto-incluse, zéro commit) | branche vide supprimée (refs distante + locale) |
| `client-angular` | code-only | hors périmètre `/merge` — géré manuellement par l'humain |

**CI `develop` après merge** (règle 5) :

- client-blazor : ✅ [run 35000306889](https://github.com/codengine-technologies/HealthPlatform.Client/actions/runs/35000306889)
- client-mobile : ✅ [run 35000343018](https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/35000343018) — **premier vert depuis le 2026-09-14**

Branches `fix/*` locales conservées sur les deux repos ; seules les refs distantes
ont été supprimées. Aucune branche de staging (task hors run `/forge`).

### Le premier `/merge` a été refusé — ce qu'il a fallu corriger

La garde 4 (CI verte) a échoué sur **les deux** PRs, pour deux raisons sans
rapport entre elles. Analyse complète : `questions/merge-task-309.md`.

**1. `client-blazor` — la garde de cette task ne gardait rien.**
`MailboxSwitcherMountGuardTests` composait son chemin avec `"src"` en minuscule
alors que le répertoire versionné est `Src/`. Windows, insensible à la casse, la
laissait verte ; le runner Linux la refusait. Plus grave que la casse : l'échec
portait sur `File.Exists`, donc **avant** l'assertion qui fait l'objet de la
garde — elle était verte en local pour une raison sans rapport avec le montage du
sélecteur. Corrigé en localisant la page par `RepoScan.TrackedFiles` (`git
ls-files`), comme les deux gardes sœurs du même projet : la casse du dépôt
devient opposable et la classe entière du défaut disparaît. `Assert.Single` tient
le garde-fou du garde-fou. **Garde ré-éprouvée** : sélecteur retiré de
`Mail.razor` → rouge sur l'assertion de fond, remis → vert. Commit `6a2b559`.

**2. `client-mobile` — panne d'outillage CI préexistante, non imputable à la task.**
Le job `build-android` mourait dans `android-actions/setup-android@v3`
(`Failed to find package 'tools'`) **avant** tout `npm ci`, build ou test :
le défaut de l'action est `packages: tools platform-tools` et `tools` a été retiré
du dépôt SDK. La panne était déjà sur `develop` depuis le 2026-09-14
(run 34896682052), première rupture après une série verte remontant au
2026-08-30 — elle frappait donc **toute** PR mobile ouverte depuis. Arbitrage
humain du 2026-09-15 : correctif porté sur la branche task-309 plutôt qu'en PR
devops séparée, `develop` récupérant la réparation au merge. Commit `1cb0ba4`.
