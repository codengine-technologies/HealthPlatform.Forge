# todo-task-500.md — Anneau : une ligne allégée, le compteur de conversation et la réponse sur l'anneau

**Repos**: api-mail, client-angular, client-mobile
**Reprises**: 1
**Dependencies**: task-497
**Epic**: E027

> **Origine.** Demande humaine du 2026-11-27, en recette de task-497 (lot 1 de l'anneau, en PR) : la ligne de liste est
> trop chargée. « La mention « Non affecté » n'apporte rien » ; l'identifiant du message « doit uniquement s'afficher
> dans le hint au survol de l'anneau » ; le compteur de conversation doit être intégré à l'anneau « comme le fait
> Apple », et « x messages » retiré ; l'anneau doit aussi dire qu'un message a reçu une réponse, avec l'icône actuelle
> (lettre et flèche vers la gauche) placée au bord de l'anneau.
>
> **Décisions de l'humain, le même jour** :
> - les **deux clients** : weda2 et mobile ;
> - la pastille du compteur est **neutre, gris foncé**, pas rouge : en variante D, le rouge dit la gravité clinique
>   (biologie critique) ;
> - l'icône « répondu » va au bord de l'anneau **dès qu'une réponse existe**, que l'anneau soit ouvert ou fermé ;
> - **nouvelle task**, après task-497, qui se merge telle quelle.
>
> **Allègements complémentaires**, proposés par la forge après relecture des deux lignes et **validés par l'humain le
> 2026-11-27** (règles 8 à 14) : 2 valeurs de biologie au plus puis « +N » ; une seule date par ligne ; plus de
> « MESSAGE » / « COURRIER » ; « Envoyé » / « Brouillon » seulement hors de leur dossier ; sur le mobile, plus de puce
> « Biologie » en mode anneau, plus de code « (H) » / « (L) », « Document médical » en icône.

## Objectif

En tant que médecin qui parcourt sa boîte, je veux une ligne de liste qui ne dit que l'utile, et un anneau qui
rassemble l'état du message : avancement, gravité, à qui le tour, nombre de messages de la conversation, réponse
envoyée. Je lis la liste plus vite, sans perdre d'information.

### Ce qui est établi (code relu le 2026-11-27)

- weda2, `mail-header.component.html` :
  - la ligne écrit l'identifiant IMAP du message, `[uid]`, deux fois (squelette d'enrichissement et ligne enrichie),
    masqué au survol (`.mail-uid-debug`) ;
  - en mode anneau, elle écrit « Non affecté » (`mail-row-unassigned-{uid}`) ;
  - en vue conversation, « N messages » (`mail-list-row-thread-count`) suivi du bouton qui déplie le fil
    (`mail-list-row-thread-toggle`) ;
  - l'icône « répondu » (`mail-replied-{uid}`, icône `communication/mail-import-ou-lc`) a pour infobulle la phrase du
    bandeau (`replySummaryText`).
- Mobile, `mail-header.component.html` :
  - pas d'identifiant affiché ;
  - « Non affecté » (`mail-chip-unassigned-{uid}`) ;
  - la puce « N messages » (`mail-thread-{uid}`) est aussi le bouton qui déplie le fil ;
  - l'icône « répondu » (`arrow-undo`, `mail-replied-{uid}`) montre sa phrase à l'appui long.
- L'état en clair de l'anneau (task-497, règle 8) dit déjà « Non affecté. » : l'information reste au survol et pour le
  lecteur d'écran.
- Parcours e2e qui lisent ces éléments : E2E-RING-003 (« Non affecté » écrit sur la ligne), E2E-CONV-001, CONV-003 et
  SHARED-004 (présence du compteur pour reconnaître un fil), E2E-DETAIL-006 (présence de l'icône « répondu »).
- Aucun parcours e2e ne lit les éléments des règles 8 à 14 (valeurs de biologie de la ligne, dates, type, « Envoyé »,
  puces « Biologie » et « Document médical », codes d'interprétation) : seuls les tests de composant suivent.
- weda2 : `documentDate` retombe aujourd'hui sur la date d'envoi, d'où la même date écrite deux fois sur un message
  ordinaire ; `docTypeText` rend « MESSAGE » ou « COURRIER » sans document médical ; `flaggedBiologyResults` n'a pas de
  limite.

### Règles

1. **« Non affecté » quitte la ligne**, sur les deux clients. L'état en clair de l'anneau le garde (« Non affecté. »), au
   survol et pour le lecteur d'écran. Le tableau de bord (task-499) n'est pas concerné.
2. **L'identifiant du message quitte la ligne** (weda2). Il s'ajoute à l'**infobulle** de l'anneau, après l'état en
   clair : « … — Identifiant : 1234 ». Il n'entre **pas** dans le libellé lu par le lecteur d'écran. Ligne sans anneau
   (Envoyés, Brouillons, Corbeille, icône classique) : il va dans l'infobulle de l'initiale de l'expéditeur. Le
   squelette d'enrichissement ne l'écrit plus non plus. Le mobile n'affiche pas d'identifiant : rien à faire.
3. **Le compteur de conversation devient une pastille sur l'anneau**, en vue conversation, pour un fil d'au moins
   2 messages :
   - pastille ronde **gris foncé**, chiffre blanc (contraste ≥ 4,5:1), posée en haut à droite de l'anneau, à la
     manière des pastilles d'iOS ; au-delà de 99, « 99+ » ;
   - libellé accessible : « Conversation de N messages » ;
   - « N messages » quitte la ligne ;
   - weda2 : le bouton qui déplie le fil (chevron) reste à sa place ;
   - mobile : un appui sur la pastille déplie ou replie le fil, comme la puce aujourd'hui, sans ouvrir le message. La
     zone d'appui fait au moins 32 × 32 px, même si la pastille est plus petite. Le chevron de la puce disparaît ;
     l'état déplié se lit dans `aria-expanded` de la pastille.
4. **L'icône « répondu » se pose au bord de l'anneau** dès qu'une réponse existe, que l'anneau soit ouvert, fermé ou
   hors suivi :
   - même icône qu'aujourd'hui (lettre et flèche vers la gauche) dans une petite pastille blanche cerclée, en bas à
     droite de l'anneau ;
   - infobulle et libellé accessible : la phrase actuelle (« Vous avez répondu à ce message le … ») ;
   - l'icône quitte sa place dans la ligne.
5. **Ligne sans anneau** (Envoyés, Brouillons, Corbeille, icône classique) : elle reste celle d'aujourd'hui (règle 12
   de task-497), « N messages » et icône « répondu » à leur place. Seul l'identifiant passe dans l'infobulle de
   l'initiale (règle 2).
6. **Lisibilité à la taille de la liste (32 px)** : la pastille du compteur et celle de la réponse ne masquent ni les
   initiales du centre, ni l'extrémité de l'arc, ni le badge ⚠ de gravité. Elles débordent du cercle, sans changer la
   hauteur de la ligne. Aucune animation nouvelle.
7. **Identifiants de test conservés** : la pastille du compteur garde `mail-list-row-thread-count` (weda2) et
   `mail-thread-{uid}` (mobile) ; l'icône « répondu » garde `mail-replied-{uid}`. Les parcours qui reconnaissent un fil
   ou une réponse restent valides.

**Allègements complémentaires (validés le 2026-11-27)**

8. **Valeurs de biologie : 2 au plus sur la ligne**, les deux clients. Ordre : critiques d'abord, puis les autres
   anormales, dans l'ordre du compte rendu. Au-delà, une mention « +N autres » (libellé accessible : « N autres valeurs
   anormales, à lire dans le message »). Le détail du message montre toujours toutes les valeurs. La règle de
   task-392 ne change pas : seule la valeur signalée par le laboratoire est mise en évidence.
9. **Une seule date par ligne** (weda2). La date de réception reste en ligne 1. La date du document (ligne 3) ne
   s'écrit que pour un document médical dont la date diffère du **jour** de réception ; sinon, rien. Le repli actuel
   sur la date d'envoi disparaît.
10. **Plus de « MESSAGE » ni de « COURRIER »** (weda2) : le type ne s'écrit en ligne 1 que pour un document médical
    (BIOLOGIE, IMAGERIE, … ou DOCUMENT). Le badge « PATIENT » d'un message de patient ne change pas.
11. **« Envoyé » / « Brouillon » seulement hors de leur dossier** (weda2) : pas d'indicateur dans le dossier Envoyés (ou
    un de ses sous-dossiers) ni dans Brouillons, reconnus par leur type, jamais par leur nom (task-417). Il reste dans
    les vues mélangées : conversation, vue par étiquette, résultats de recherche.
12. **Mobile — plus de puce « Biologie » / « Biologie CRITIQUE » en mode anneau** : l'anneau (couleur de gravité), le
    badge ⚠ N et les valeurs la disent déjà. En icône classique, elle reste.
13. **Mobile — plus de code d'interprétation « (H) », « (L) »… après la valeur** : la flèche devant la valeur le dit. Le
    libellé accessible de la valeur garde le sens (« élevé », « bas », « critique »).
14. **Mobile — « Document médical » devient une icône** (document) sans texte ; « Document médical » et, s'il y a lieu,
    « version N » passent dans l'infobulle et le libellé accessible. La puce « À rattacher (N) » ne change pas.

### Hors périmètre

- Le grand anneau du détail et la section « Traitement » (task-497) : inchangés.
- L'ancienneté J+N, les seuils et la légende : task-498. La légende y dessinera aussi les deux pastilles.
- Le tableau de bord : task-499.

## Definition of Done

- [ ] Build passes : `nx build weda2`, client-mobile (0 erreur) ; api-mail inchangé hors catalogue.
- [ ] Tests pass : `nx test mss-lib`, `nx test weda2`, client-mobile (0 échec).
- [ ] Tests de composant de la ligne, weda2 et mobile, chacun vu rouge :
      - plus de « Non affecté » sur la ligne, toujours dans l'état en clair ;
      - plus d'identifiant écrit sur la ligne (weda2), présent dans l'infobulle de l'anneau, absent du libellé
        accessible ; sans anneau, dans l'infobulle de l'initiale ;
      - pastille du compteur sur l'anneau d'un fil de 2 messages, « 99+ » au-delà de 99, aucune pastille hors vue
        conversation ou pour un message seul ; plus de « N messages » dans la ligne en mode anneau ;
      - mobile : un appui sur la pastille déplie le fil sans ouvrir le message, `aria-expanded` suit ;
      - icône « répondu » au bord de l'anneau ouvert comme fermé, plus dans la ligne ; infobulle = phrase du bandeau ;
      - ligne sans anneau : « N messages » et icône « répondu » à leur place d'aujourd'hui.
- [ ] Tests de composant des allègements complémentaires, chacun vu rouge :
      - 2 valeurs de biologie au plus, critiques d'abord, « +N autres » avec son libellé accessible ; 2 valeurs ou moins :
        aucune mention (weda2 et mobile) ;
      - weda2 : date du document absente sur un message ordinaire et sur un document daté du jour de réception, présente
        sinon ;
      - weda2 : aucun type écrit sur un message sans document médical, « BIOLOGIE » sur un compte rendu de biologie ;
      - weda2 : pas d'« Envoyé » dans Envoyés ni dans un sous-dossier, « Envoyé » en vue conversation et en vue par
        étiquette ; même règle pour « Brouillon » ;
      - mobile : pas de puce « Biologie » en mode anneau, présente en icône classique ; plus de « (H) » ; « Document
        médical v2 » dans l'infobulle et le libellé accessible de l'icône.
- [ ] Test de composant de l'anneau, weda2 et mobile : à 32 px, les pastilles sont hors du cercle des initiales et du
      badge ⚠ (positions relues), vu rouge.
- [ ] Contraste du chiffre blanc sur la pastille gris foncé ≥ 4,5:1 ; couleur par jeton du design system quand il
      existe (weda2 : `--ds-*`).
- [ ] `data-testid` conservés (règle 7) ; nouveaux `data-testid` sur la pastille de réponse si elle change d'élément.
- [ ] Scénario **E2E-RING-003** monté en **version 2** dans `Api/Mail/e2e/scenarios.yml` : « Non affecté » n'est plus
      lu sur la ligne mais dans l'état en clair de l'anneau. Tests des deux clients mis à jour.
- [ ] Scénario **E2E-RING-005** (version 1, `mobile: requis`, `angular: requis`) ajouté au catalogue et implémenté dans
      les deux clients : le test dépose un message à traiter d'objet unique, puis une réponse du même fil. En vue
      conversation, l'anneau du fil porte la pastille « 2 » ; la ligne n'écrit pas « 2 messages » ; un appui sur la
      pastille (mobile) ou sur le chevron (weda2) déplie le fil. Le praticien répond au message : relu du serveur, il
      est répondu, et son anneau porte l'icône « répondu », dont l'infobulle est la phrase du bandeau.
- [ ] Mobile : référence Stitch de l'écran `mail-list` mise à jour (`/stitch-design`, best-effort).
- [ ] `python Tools/contracts/contract_impact.py check` : aucun impact (aucun contrat ne change).

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil de développement habituel).
- weda2 : `cd Client/Angular/front && npm run start:weda2`. Mobile : `cd Client/Mobile && npm start`.
- Données : une boîte partagée avec un délégataire ; un message à traiter non attribué ; une conversation de 3 messages
  dont un à traiter ; un message auquel on a répondu, encore à traiter ; un autre répondu et traité.
- Référence visuelle : `Docs/specs/anneau-de-traitement/maquettes.html`, variante D, section 2 (liste).

1. weda2, Boîte de réception, vue liste : aucune ligne n'écrit « Non affecté » ni `[1234]`. Au survol de l'anneau du
   message non attribué, l'infobulle dit « … Non affecté. — Identifiant : … ».
2. Le message répondu encore à traiter : anneau ouvert, icône « répondu » à son bord, infobulle « Vous avez répondu à
   ce message le … ». Le message répondu et traité : coche, et la même icône au bord.
3. Passer en vue conversation : l'anneau du fil porte une pastille grise « 3 » ; la ligne n'écrit plus « 3 messages » ;
   le chevron déplie le fil.
4. Corbeille : les lignes gardent l'initiale ; l'infobulle de l'initiale donne l'identifiant.
5. Réglages, « Icône classique » : la ligne est celle d'avant l'anneau (« N messages », icône « répondu » dans la ligne),
   sans identifiant écrit.
6. Mobile, mêmes données : points 1 à 3 (sans identifiant) ; en vue conversation, un appui sur la pastille déplie le fil
   sans ouvrir le message ; un second appui le replie.
7. Données complémentaires : un bilan de biologie à 5 valeurs anormales dont 1 critique ; un compte rendu daté de la
   veille de sa réception ; un message ordinaire. weda2 : le bilan montre la valeur critique, une autre, puis « +3 autres » ;
   le compte rendu montre sa date de document, le message ordinaire une seule date et aucun « MESSAGE ». Dossier Envoyés :
   aucune ligne n'écrit « Envoyé » ; en vue conversation, la réponse envoyée l'écrit.
8. Mobile : le bilan n'a pas de puce « Biologie » (mode anneau), ses valeurs n'ont pas de « (H) », et le document médical
   est une icône dont l'appui long dit « Document médical ». En icône classique, la puce « Biologie » revient.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du cabinet).
- **Vague Ségur** : hors Ségur — ergonomie de la liste, aucune exigence DSR nouvelle.
- **Exigences DSR honorées** : non applicable.
- **INS** : non applicable — aucun patient identifié ni manipulé.
- **Authentification PS** : inchangée — session PSC (e-CPS) de la messagerie.
- **Habilitations** : inchangées — la ligne affiche ce que la personne voit déjà.
- **Interop CI-SIS** : non applicable.
- **Tracé PGSSI-S** : aucun acte nouveau (affichage seul).
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : inchangé — aucune donnée nouvelle, aucune donnée de santé dans les infobulles (l'identifiant
  IMAP est technique).
- **AIPD / impact RGPD** : inchangée.

## Branches

- `api-mail` (pushed) : feat/task-500-anneau-ligne-allegee-compteur-de — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-500-anneau-ligne-allegee-compteur-de
- `client-mobile` (pushed) : feat/task-500-anneau-ligne-allegee-compteur-de — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-500-anneau-ligne-allegee-compteur-de
- `client-angular` (code-only) : la forge écrit sur la branche extraite dans `Client/Angular/` (au /start :
  `feature/nova-mss-weda-integration`, après le commit task-497 `2b991559`) — l'humain gère branche, commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-500 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 19 s | — | — | — | — |
| /develop | ok | 7 min 14 s | 4 (40 s) | 6 (2 min 39 s) | — | client-mobile 2B/2T, client-angular 2B/4T, reprise 1 (B1, S1, S3) |
| /review-code | ok | 1 min 08 s | — | — | — | — |
| /sonar | skipped | 0.9 s | — | — | — | aucun fichier analysé par Sonar |
| **Total cycle** | | **8 min 43 s** | **4 (40 s)** | **6 (2 min 39 s)** | **0 (0.0 s)** | |

## Develop log

Implémenté le 2026-11-27 par deux agents en parallèle (weda2, mobile), chacun test d'abord puis preuve par mutation,
puis une passe qualité commune (§Q). Journaux : `scratchpad/weda2-500/`, `scratchpad/mobile-500/`, `scratchpad/simplify-500/`.

### api-mail (catalogue)

- `e2e/scenarios.yml` (`c8aa3845`) : `E2E-RING-003` v2 (« Non affecté » lu dans l'état en clair de l'anneau),
  `E2E-RING-005` v1 (pastille du compteur de conversation, icône « répondu » au bord de l'anneau). Aucun code C#.

### client-angular (code seul) — fichiers à commiter sur TFS

| Fichier | Raison |
|---|---|
| `libs/mss/src/ui/mail-ring/mail-ring.component.{ts,html,scss}` (+ spec) | pastilles compteur et réponse au bord de l'anneau, infobulle `hint` (identifiant), positions à 32 px |
| `libs/mss/src/features/mail/components/mail-header/mail-header.component.{ts,html,scss}` (+ `mail-header.ring.spec.ts`) | ligne allégée : « Non affecté », `[uid]`, « N messages », icône répondu retirés en mode anneau ; biologie 2 + « +N » ; une date ; type et « Envoyé » / « Brouillon » ; espaceur de ligne 1 |
| `libs/mss/src/features/mail/components/mail-header/mail-header.light-row.spec.ts` (nouveau) | 27 tests des règles 1 à 11 |
| `libs/mss/src/features/mail/services/mail-state.service.ts` (+ `mail-state.service.listed-folder.spec.ts`, nouveau) | `listedFolderType` : type du dossier listé (Envoyés / Brouillons et sous-dossiers), vues mêlées |
| `libs/mss/src/core/utils/mail-ring.util.ts`, `mail-ring-row.util.ts` (+ specs) | mention `unassigned` retirée de `MailRingChips` |
| `e2e/mss-e2e/specs/functional.e2e.ts` | E2E-RING-003 v2, E2E-RING-005 v1 |

### client-mobile

- `mail-header.component.{ts,html,scss}` : `.mail-ring-wrap` porte le bouton compteur `mail-thread-{uid}` (zone 32×32,
  `aria-expanded`, `pointerdown` stoppé, pas d'ouverture du message) et la pastille réponse `mail-replied-{uid}` ; en mode
  anneau, plus de puce « N messages », d'icône répondu de ligne, de « Non affecté », de puce « Biologie » ; biologie 2 +
  « +N » ; plus de « (H) » (sens porté par la flèche) ; « Document médical » en icône.
- Specs : `mail-header.ring-badges.spec.ts` et `mail-header.lightened.spec.ts` (nouveaux), `mail-header.ring.spec.ts`,
  `mail-header.component.spec.ts`, `mail-list.ring.spec.ts`. e2e : E2E-RING-003 v2, E2E-RING-005 v1.

### Preuves rouges (tests vus rouges sur le code d'avant, puis mutations)

- weda2 : 42 rouges sur 177 avant le code ; 36 mutations, chacune rouge sur son test : règle 1 (M1), 2 (M2a-e),
  3 (M3a-f), 4 (M4a-c), 5 (M5a-b), 6 (M6a-c, positions à 32 px), 8 (M8a-d), 9 (M9a-c), 10 (M10, M10b),
  11 (M11a-g ; M11d a d'abord survécu — le test passait par `openTagView`, durci, puis rouge).
- mobile : 38 rouges sur 109 avant le code ; mutations M1, M3a-h, M4, M5, M6a-d (positions dans un vrai navigateur, à la
  taille réelle de l'anneau mobile, 40 px), M8a-c, M12, M13a-b, M14a-b, chacune rouge.
- e2e, rejoués seuls sur le banc (`--serve-only` + `--grep`) : mobile RING-001/002/003/005, CONV-003, SHARED-004,
  DETAIL-006 **7 / 7 verts** ; weda2 les mêmes + CONV-001 **8 / 8 verts**. Mutations e2e, recompilation prouvée (mobile :
  compteur `ngserve.log` ; weda2 : marqueur dans le bundle servi, puis absent après restauration) : compteur faux →
  RING-005 rouge (« la pastille porte / dit « 2 » ») ; « Non affecté » réécrit sur la ligne → RING-003 rouge (« la ligne
  n'écrit plus « Non affecté » »), sur les deux clients ; restaurés, 2 / 2 verts.

### Choix faits là où la US ne tranchait pas (à relire en revue)

1. « +1 autre » au singulier ; testid `mail-bio-more-{uid}` ; libellé « N autres valeurs anormales, à lire dans le message ».
2. weda2 : l'anneau est `role="img"` ; son nom accessible reprend le libellé des pastilles (« Conversation de N
   messages. », phrase de réponse), l'identifiant n'y entre pas. Mobile : bouton et icône lus séparément.
3. weda2 : « Pour moi » et « Mails d'un patient » comptent parmi les vues mêlées (règle 11) ; sous-dossiers d'Envoyés
   reconnus par le type de leur parent (`isSentMail`).
4. weda2 : jour de réception lu sur `sentDate` (date de la ligne 1), comparé en jour local (règle 9).
5. Mobile : règles 8, 13, 14 dans les deux modes (anneau et icône classique) ; seule la 12 est limitée au mode anneau.
6. Mobile : test de position à 40 px (taille réelle de l'anneau de la liste), la DoD disait 32 px (taille weda2).
7. Couleurs par jetons : weda2 `--ds-color-background-neutral-strong` (7,2:1), mobile `--app-on-surface-variant` (9,4:1).

### Passe qualité (§Q)

- weda2 et mobile : les quatre getters de biologie de la ligne (re-parcours des documents ~6 fois par rendu) regroupés
  en un seul `rowBiology` lu par `@let` ; mobile : appels doublés de `bioMeaning` / `getBioIcon` retirés. Sans changement
  de comportement ; specs ciblées vertes (weda2 788, mobile 137).

### Validations

- client-mobile (`9d17da7`, poussé) : `npm run build` OK ; suite complète **1 977 / 1 977**, deux fois. Un test de position
  (`ne masquent pas le badge ⚠`) était vert seul et rouge en suite complète : `ion-badge` mesuré avant son hydratation ;
  corrigé (attente de `componentOnReady`), consigne `mesure-composant-ionic-apres-hydratation` (`conventions/angular.md`).
- client-angular (arbre de travail, 16 fichiers) : `nx test mss-lib` **2 211 / 2 211**, `nx test weda2` **2 683 / 2 683**,
  `nx build weda2` OK, ESLint 0 erreur, stylelint 0 erreur.
- api-mail (`c8aa3845`, poussé) : catalogue seul ; build et suite rejoués par `/review`.
- Vert marqué : client-mobile, client-angular.
- Next step : `/review task-500 --code`.

### Reprise 1 après /review

| Point | Défaut | Correctif | Test | Preuve rouge |
|---|---|---|---|---|
| B1 (weda2) | en mode sélection, la case remplace l'anneau mais `ring` restait non nul : « N messages », l'icône « répondu » et les initiales disparaissaient de la ligne | `@let ring = selectionMode ? null : row.view` : la ligne reprend ce que l'anneau porterait | `mail-header.light-row.spec` « R5 (revue, B1) — mode sélection » (case présente, anneau absent, puis « 3 messages », icône, initiales dans la ligne) | rouge sur le code d'avant ; mutation B1 (alias sans le mode sélection) : 1 rouge |
| S1 (weda2) | « 99+ » s'élargissait sur ~7 px au-delà de la gouttière (10 px), sous la ligne 1 | largeur au plus `maxWidth` 19 (bord droit à 32 + 10), fixée pour « 99+ », écrit en 9 px, plus serré (`--wide`) ; deux chiffres tiennent (padding 3 px) | test de géométrie à 32 px : bord droit ≤ 42, largeur fixée, classe `--wide` | mutations S1a (largeur non fixée), S1b (largeur 30), S1c (pas écrit plus petit) : 1 rouge chacune |
| S3 (mobile) | `TreatmentRing.unassigned` plus lu | champ retiré ; les specs lisent « Non affecté » dans l'état en clair | `treatment-ring.util.spec`, `mail-header.ring.spec` | (retrait sans comportement ; l'assertion sur le libellé existait déjà) |

- Relecture « qu'est-ce que ça casse » : en mode sélection, les mentions de l'anneau (« Attente patient », ⚠ atténué) et la
  pastille « Traité » s'affichent comme en icône classique ; aucun parcours e2e ne joue le mode sélection en lisant ces
  éléments. Le test de position mobile du badge ⚠ bloquait (5 s) quand un sous-ensemble de specs ne définit jamais
  `ion-badge` : attente bornée à 1 s ; consigne `mesure-composant-ionic-apres-hydratation` précisée.
- Validations : mobile (`205c8eb`, poussé) build OK, **1 977 / 1 977** ; weda2 `nx test mss-lib` **2 212**, `nx test weda2`
  **2 683**, `nx build weda2` OK ; ESLint, stylelint, Prettier propres sur les fichiers touchés.
- Vert marqué : client-mobile, client-angular. Next step : `/review task-500 --code`.

## Code Review Summary

### Passage 1 (revue anticipée) — CHANGES REQUESTED

Relu à : api-mail `c8aa3845` (catalogue seul), client-mobile `9d17da7`, client-angular arbre de travail (16 fichiers).
Relecteur indépendant, sans le `## Develop log`.

- **4a** : aucun comportement atteignable par un endpoint ne change (api-mail : catalogue seul). ✅
- **4c** : `api-mcp : aucun impact` / `client-mobile : aucun impact` / `client-angular : aucun impact`. ✅
- **4b (DoD)** : E2E-RING-003 v2 et E2E-RING-005 v1 au catalogue, aux versions déclarées par les tests des deux clients. ✅
- Conformité aux règles 1 à 14 constatée sur les deux clients ; aucun autre appelant cassé ; performance sans inquiétude ;
  aucun « vert qui ment ».

#### À corriger par la reprise

- **B1 — weda2 — mode sélection** (`mail-header.component.html`) : la case à cocher remplace l'anneau, mais `ring`
  (`ringRow.view`) reste non nul ; `@if (!ring)` masque alors « N messages » et l'icône « répondu » de la ligne, et
  l'anneau qui les porterait n'est pas affiché. En vue conversation, cocher des messages fait disparaître le compteur du
  fil et l'icône « répondu ». Même défaut, antérieur (task-497), pour la pastille d'initiales `!ring &&
  mail.assignment?.isOpen`. Correctif : un seul alias « anneau affiché » (`ring && !selectionMode`) pour l'anneau, le
  compteur, l'icône « répondu » et la pastille d'initiales. Test vu rouge.
- **S1 — weda2 — « 99+ » chevauche la ligne 1** (`mail-ring.component.ts`, `BADGES_AT_32.count`) : la pastille s'élargit
  vers la droite et « 99+ » (~26 px) déborde d'environ 7 px sur le début de la ligne 1, qui la recouvre. Elle doit
  s'élargir vers la gauche (ancrage à droite) ; test de géométrie à « 99+ ».
- **S3 — mobile — code mort** (`treatment-ring.util.ts`, `TreatmentRing.unassigned`) : plus lu par aucun gabarit ;
  le retirer (le libellé garde « Non affecté. »).

#### Arbitrage humain

- **A1 — mobile — zone d'appui de la pastille du compteur** : 32 × 32 px (règle 3) couvre le quart haut-droit de
  l'anneau ; à cet endroit, un appui déplie le fil au lieu d'ouvrir le message, et l'appui long ne dit plus l'état de
  l'anneau. Recommandation : garder 32 px (cible tactile), la pastille ne sert qu'aux fils.
- **A2 — weda2 — couleur de l'icône « répondu »** : passée de la couleur de marque à une couleur neutre dans sa pastille
  blanche. Recommandation : neutre (la couleur reste réservée à la gravité).

Suggestions sans suite dans cette reprise : RING-005 mobile pourrait comparer l'infobulle au texte du bandeau du détail,
comme weda2 (aujourd'hui une expression régulière).

### Passage 2 (revue anticipée, après la reprise 1) — APPROVED

**Approved at** : api-mail `c8aa3845`, client-mobile `205c8eb`, client-angular arbre de travail (après la reprise 1).

- Diff de la reprise lu en premier : rien de cassé. En mode sélection, la ligne affiche ce qu'affiche l'icône classique
  (« N messages », icône « répondu », initiales, « Traité ») ; les mentions de l'anneau restent cohérentes. Aucun appelant
  oublié de `TreatmentRing.unassigned`. L'attente bornée ne fabrique pas de faux vert (précondition `width > 0`).
- B1, S1, S3 corrigés, chacun prouvé.

#### Suggestions non bloquantes (recopiées dans la PR)

- **N1 — weda2 — « 99+ »** : 9 px dans 19 px, lisible en théorie mais très petit ; à vérifier à l'écran sur un fil de plus
  de 99 messages (jsdom ne mesure pas les polices).
- **N2 — mobile — RING-005** : comparer l'infobulle « répondu » au texte du bandeau du détail, comme weda2.

## Sonar log

- **Sonar : non joué — aucun fichier analysé par Sonar.** Dans api-mail, la task ne change que `e2e/scenarios.yml`
  (`git diff --name-only origin/develop...HEAD -- '*.cs'` vide, mêmes exclusions que `sonar.exclusions`) : skip mesuré
  (décision humaine du 2026-11-19, task-485). Pas de tableau de KPIs ; la PR api-mail le dit.
