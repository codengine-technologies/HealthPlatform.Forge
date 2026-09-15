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
| **Total cycle** | | **1 min 23 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
