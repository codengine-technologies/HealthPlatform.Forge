# todo-task-160.md — Couche interaction & polish UX mobile (skeletons, haptics, optimistic UI, micro-animations)

**Repos**: client-mobile
**Single frontend**: true
**Dependencies**: — (socle design system E014 livré par task-110 ; optimistic UI mail déjà en place via `mail-actions.service`)
**Epic**: E014

> US **single-frontend `client-mobile`** (GitHub, automation forge complète :
> branche/commit/push/PR). **Aucun changement backend** ni contrat : purement
> couche présentation/interaction. L'objectif est de faire passer l'app d'un
> ressenti « Ionic fonctionnel » à un ressenti « natif premium » — sans changer
> la stack (Ionic 8 / Angular 21 / Capacitor 8), en exploitant ce qui est déjà
> installé (`@capacitor/haptics`, `ion-skeleton-text`, `@angular/animations`).

## Objectif

La couche interaction de `client-mobile` est aujourd'hui quasi vide : chargements
matérialisés par des spinners (`ion-spinner`) au lieu de skeletons, haptiques
posées en ad-hoc dans 2 composants seulement (`mail-folder-item`, `mail-header`)
sans service central ni réglage, aucune micro-animation custom (0 `createAnimation`),
et l'optimistic UI — pourtant excellent côté mail — n'est ni généralisé ni
documenté comme convention. Cette US industrialise les 4 leviers du ressenti
« premium » :

1. **Skeleton screens** sur **tous** les écrans à chargement asynchrone
   (fin des spinners de contenu).
2. **Haptiques systématiques** sur les actions clés, via un **service central**
   désactivable par le PS et respectant l'OS.
3. **Optimistic UI** : auditer, standardiser (pattern rollback + toast), et
   **étendre** aux actions réseau non encore couvertes (acquittement biologie).
4. **Micro-animations cohérentes** (entrée de liste, ouverture de détail),
   respectant `prefers-reduced-motion`.

Aucune donnée métier n'est manipulée : c'est un chantier de présentation.

## Décisions produit validées (2026-07-16)

- **Une seule task** couvrant les 4 axes (US « polish interaction » cohérente,
  1 seule validation humaine). DOD scindé par axe pour la lisibilité de la revue.
- **Skeletons partout** : tous les écrans à chargement async, pas seulement les
  2 cités — cohérence visuelle totale.
- **Haptiques désactivables** : interrupteur « Retour haptique » dans l'onglet
  **Paramètres** existant (activé par défaut), + respect d'un éventuel réglage OS.
- **Accessibilité** : les micro-animations respectent `prefers-reduced-motion`
  (pas d'animation si l'OS le demande) ; le service haptique n'émet rien si le
  toggle est off.

## Scope (client-mobile, `Client/Mobile/`)

### Axe 1 — Skeleton screens (remplacer les spinners de contenu)

Remplacer les spinners de **chargement de contenu** par des squelettes
(`ion-skeleton-text` animés) reproduisant la forme de la liste/vue cible. Écrans
concernés (chargement async identifié) :

- `features/mail/components/mail-list/` (liste INBOX / dossiers)
- `features/mail/components/mail-detail/` (corps du mail)
- `features/mail/components/mail-draft-list/`
- `features/mail/components/mail-search/` + `mail-search-history/`
- `features/mail/components/mail-summary/`
- `features/patient/components/biology-timeline/`
- `features/patient/components/clinical-synthesis/`
- `features/patient/components/patient-timeline/` (+ groupes/`timeline-document-group`)
- `features/patient/components/medical-history/`

Convention : composant **skeleton réutilisable** paramétrable (nb de lignes,
présence avatar) plutôt qu'un skeleton dupliqué par écran (memory
`feedback_reuse_existing_components`). **Ne pas** toucher aux spinners
d'**action** (boutons en cours de soumission) — ils restent des spinners courts.
Skeleton visible uniquement au **premier** chargement / rechargement plein,
pas sur les refreshers `ion-refresher` (qui ont déjà leur indicateur natif).

### Axe 2 — Haptiques centralisées et réglables

- Créer **`HapticsService`** (`src/app/core/services/haptics.service.ts`)
  encapsulant `@capacitor/haptics` : méthodes sémantiques
  (`impactLight` / `impactMedium` / `success` / `warning` / `error` / `selection`),
  chacune **no-op** si le toggle est off (ou plateforme web sans support).
  Toujours `.catch(() => undefined)` (jamais d'exception haptique remontée).
- **Réglage utilisateur** : ajouter un `ion-toggle` « Retour haptique » dans
  `src/app/settings/settings.page.*` (activé par défaut), persisté via le
  mécanisme de réglages existant (mémoire `project_mobile_ion_tabs_shell` :
  POST Settings = remplacement en bloc → muter par spread, ne pas écraser les
  autres réglages).
- **Câblage des actions clés** via le service :
  - **Envoi de mail** (`mail-compose`) → `success` au succès d'envoi.
  - **Acquittement biologie** (`biology-ack-*`) → `success` à l'acquittement.
  - **Swipe-to-flag / flag** (`mail-list` / `ion-item-sliding` / `mail-header`) →
    `impactMedium` au déclenchement de l'action de swipe.
  - **Sélection longue** (entrée en mode sélection, `long-press`) → `selection`.
  - **Erreur d'action** (échec réseau après rollback optimiste) → `warning`.
- **Refactor** des 2 appels ad-hoc existants (`mail-folder-item.component.ts`,
  `mail-header.component.ts`) pour passer par `HapticsService` (fin des appels
  directs `Haptics.impact`).

### Axe 3 — Optimistic UI : audit, standardisation, extension

- **Déjà conforme** (ne pas réécrire, juste vérifier/aligner sur la convention) :
  `mail-actions.service.ts` (`toggleRead`, `markRead`, `toggleFlag`, `deleteMail`,
  `moveMail`, `bulk*`) fait déjà MAJ optimiste + rollback + ajustement compteurs.
- **Standardiser** le pattern « MAJ optimiste → appel API → rollback + toast FR
  d'erreur + haptique `warning` sur échec » comme convention documentée (commentaire
  d'en-tête du service + réutilisation du même helper de rollback).
- **Étendre** l'optimistic UI à l'action réseau **non encore optimiste** :
  **acquittement biologie** (`biology-ack-panel` / `biology-ack-confirm-dialog`
  et le service associé) — le badge/état passe « acquitté » immédiatement, rollback
  + toast si l'appel échoue.
- **Toast d'erreur** cohérent (libellé FR, non technique) branché sur chaque
  rollback ; aujourd'hui certains rollbacks sont silencieux.

### Axe 4 — Micro-animations cohérentes

- Utilitaire d'animations partagé (`src/app/core/utils/animations.ts` ou
  `AnimationController` Ionic) : **entrée de liste** (fade + translate léger,
  stagger discret sur l'apparition des items) et **ouverture de détail**
  (transition de page vers `mail-detail` / `medical-document-modal`).
- **Respect `prefers-reduced-motion`** : détection (media query / API) → animations
  neutralisées (apparition instantanée) si l'OS demande la réduction de mouvement.
- Durées/courbes centralisées en tokens (cohérence avec le design system E014 —
  ajouter au besoin `--app-motion-*` dans `theme/variables.scss`, pas de valeurs
  magiques dispersées).
- **Pas** de sur-animation : subtil, < 250 ms, jamais bloquant pour l'interaction.

## Scope OUT

- **Aucun changement backend** (`api-mail`, proxy, `dtos-mss`) ni contrat.
- **Pas de refonte visuelle** des écrans (couleurs, layout, typo) — le design
  system E014 reste la référence ; on ajoute la couche *interaction*, pas le *look*.
- **Pas de dark mode** (décision séparée, hors périmètre de cette US).
- **Pas de nouvelle dépendance** : on exploite `@capacitor/haptics`,
  `ion-skeleton-text`, `@angular/animations` déjà présents.
- **Pas de réécriture** de l'optimistic UI mail existant (déjà conforme) — audit
  et alignement uniquement.
- **Pas de refresher/`ion-refresher`** transformé en skeleton (indicateur natif conservé).

## Definition of Done

**Général**
- [ ] Build passe : `cd Client/Mobile && npm run build` (0 erreur)
- [ ] Tests passent : `npm test -- --watch=false --browsers=ChromeHeadless` (0 échec)
- [ ] Lint OK : `ng lint` (aucune nouvelle erreur)
- [ ] `data-testid` conservés/ajoutés sur les interactifs touchés
- [ ] Libellés **FR en dur** (pas de `ngx-translate` — convention mobile/Angular MSS)
- [ ] Aucune régression fonctionnelle des flux mail/patient existants

**Axe 1 — Skeletons**
- [ ] Composant skeleton réutilisable (paramétrable lignes/avatar) créé — testé (rendu)
- [ ] Chaque écran à chargement async listé affiche un skeleton au 1er chargement,
      plus aucun `ion-spinner` de **contenu** résiduel sur ces écrans
- [ ] Le skeleton disparaît au chargement des données (état loading → loaded) — testé

**Axe 2 — Haptics**
- [ ] `HapticsService` créé, chaque méthode no-op quand le toggle est off — testé
      (≥ 1 test on/off par nature d'impact + swallow d'erreur)
- [ ] Toggle « Retour haptique » présent dans Paramètres, activé par défaut,
      persisté sans écraser les autres réglages (spread) — testé
- [ ] Actions clés câblées via le service (envoi, acquittement bio, swipe-to-flag,
      sélection longue, erreur) — testé (spy sur `HapticsService`)
- [ ] Les 2 appels `Haptics.impact` ad-hoc passent désormais par le service
      (plus d'import direct `@capacitor/haptics` hors du service)

**Axe 3 — Optimistic UI**
- [ ] Acquittement biologie : MAJ optimiste + rollback + toast FR sur échec — testé
      (succès + échec avec rollback)
- [ ] Chaque rollback (mail + bio) déclenche un toast FR d'erreur + haptique `warning` — testé
- [ ] Convention optimistic UI documentée en en-tête de `mail-actions.service.ts`
      et réutilisée par le service biologie (pas de pattern divergent)

**Axe 4 — Micro-animations**
- [ ] Animation d'entrée de liste + transition d'ouverture de détail en place
- [ ] `prefers-reduced-motion` respecté : aucune animation quand l'OS le demande — testé
- [ ] Durées/courbes centralisées (tokens `--app-motion-*` ou util partagé),
      aucune valeur magique dispersée dans les composants

## Manual Test Plan

**Pré-requis** : `api-mail` + proxy lancés en local, un compte MSSanté de test
configuré (INBOX non vide, au moins un mail de biologie hors normes à acquitter).
Tester de préférence sur **device/émulateur Android** pour le retour haptique réel
(cf. mémoire AVD : RAM 4096M + GPU host).

1. Lancer le mobile : `cd Client/Mobile && npm start` (ou build + run device).

### Axe 1 — Skeletons
2. Ouvrir l'INBOX (ou tirer pour recharger via navigation, pas le refresher) →
   ✅ un **skeleton** de liste s'affiche pendant le chargement, remplacé par les
   mails une fois chargés (aucun spinner de contenu).
3. Ouvrir un mail, la timeline patient, la synthèse clinique, la biologie →
   ✅ skeleton adapté à chaque écran pendant le chargement.

### Axe 2 — Haptics
4. Paramètres → ✅ toggle « Retour haptique » présent, activé.
5. Envoyer un mail, acquitter une biologie, swiper pour flagger, entrer en mode
   sélection (appui long) → ✅ retour haptique perçu à chaque action (device réel).
6. Désactiver le toggle → refaire les mêmes actions → ✅ **plus aucune** vibration.
   Réactiver → vibrations de retour. Fermer/rouvrir l'app → ✅ le réglage persiste.

### Axe 3 — Optimistic UI
7. Marquer lu / flagger un mail → ✅ l'UI réagit **instantanément** (déjà le cas).
8. Acquitter une biologie → ✅ le badge passe « acquitté » immédiatement, avant
   la réponse serveur.
9. Simuler un échec réseau (couper le backend / bloquer l'URL d'acquittement) →
   ✅ l'état **revient** à sa valeur initiale (rollback) + toast FR d'erreur
   lisible + haptique `warning`.

### Axe 4 — Micro-animations
10. Naviguer vers l'INBOX puis ouvrir un mail / un document → ✅ transitions
    fluides et discrètes (entrée de liste, ouverture de détail), < 250 ms,
    jamais bloquantes.
11. Activer « Réduire les animations » dans les réglages Android → relancer →
    ✅ apparition instantanée, aucune animation.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (client mobile de messagerie sécurisée de
  santé) — US purement présentation/interaction, sans impact sur les échanges métier
- **Vague Ségur** : hors exigence DSR spécifique — amélioration ergonomique du
  canal mobile ; ne modifie aucun flux référencé
- **Exigences DSR honorées** : non applicable — aucune fonction métier Ségur
  créée/modifiée ; les flux MSSanté/biologie sous-jacents restent inchangés
- **INS** : non applicable — aucune manipulation d'identité patient
- **Authentification PS** : inchangée (e-CPS/CIBA existant) — cette US ne touche
  ni l'auth ni les habilitations
- **Habilitations** : non applicable — aucun contrôle d'accès modifié
- **Interop CI-SIS** : non applicable — pas d'échange de contenu métier (CDA/FHIR)
- **Tracé PGSSI-S** : non applicable — aucun nouvel évènement métier ; le réglage
  haptique est une préférence UI locale non sensible (aucune donnée de santé)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun (CIM-10/SNOMED/LOINC/CCAM/NABM/CIS-CIP non concernés)
- **Hébergement HDS** : non — aucune DSCP créée ni manipulée ; couche présentation pure
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement de donnée personnelle ;
  le seul état persisté est une préférence d'affichage (retour haptique on/off)

## DOD santé — items ajoutés

- [ ] Aucune donnée de santé (contenu mail, résultat biologie, identité patient)
      introduite dans un log console, un libellé de skeleton, ou une trace d'animation
- [ ] Les skeletons n'exposent aucune donnée réelle (formes neutres uniquement)
- [ ] Accessibilité : `prefers-reduced-motion` respecté ; haptiques désactivables

## Stitch design

- Projet : `client-mobile` (id `10088502293310567548`, MOBILE), design system
  « Clinical Precision » (E014).
- Pas de **nouvel écran** à générer : cette US ajoute la couche interaction sur
  des écrans existants. `/stitch-design` peut être **skippé** (aucun écran nouveau).
  Les états « skeleton » et « animations » sont des variantes d'interaction, pas
  des maquettes distinctes ; référence visuelle = les écrans existants du projet.

## Branches
- `client-mobile` (pushed) : feat/task-160-interaction-polish — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-160-interaction-polish

## Simplify log
- Passe `/simplify` (quality-only) sur le diff frais (45 fichiers, 4 axes) : **skip clean**.
- Réutilisation déjà optimale : `ActionFeedbackService` partagé mail+biologie, `mss-skeleton-list`
  réutilisable unique, tokens `--app-motion-*` centralisés, `HapticsService` seul importeur haptics.
- Aucune duplication ni sur-couche à réduire. Aucun commit.
- Next : /lint-mobile 160.

## Visual verify log
Playwright headless 390×844, session complète + API mockée (fixtures). 9 écrans
touchés capturés, **aucun blank/crash**, 0 erreur console.

| Écran | Route | Résultat |
|---|---|---|
| inbox (mail-list) | /tabs/messages | ✓ ok, non-blank |
| mail-detail | /mail/INBOX/101 | ✓ ok, non-blank |
| settings (toggle haptique) | /tabs/settings | ✓ ok, non-blank |
| biology (ack panel optimiste) | /mail/INBOX/102 | ✓ ok, non-blank |
| patient-timeline | /tabs/patients | ✓ ok, non-blank |
| clinical-synthesis | /tabs/patients | ✓ ok, non-blank |
| biology-timeline | /tabs/patients | ✓ ok, non-blank |
| mail-search | /mail-search | ✓ ok, non-blank |
| mail-draft-list | /tabs/messages | ✓ ok, non-blank |

- Skeletons = états transitoires (rendus au 1er chargement, disparaissent post-chargement) ;
  captures = état chargé → validation « pas de régression visuelle / pas d'écran mort ».
- Captures : `Client/Mobile/e2e/screenshots/task-160/` (commit cebeba4) + galerie
  `Docs/epics/img/screens/client-mobile/` (état visuel E014).
- Next : /review 160.

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/58 (label: awaiting-human-merge)

## Code Review Summary
- Verdict : **APPROVED** — 45 fichiers, 4 axes, 0 bloquant.
- Correctness / Réutilisation / Sécurité / Tests : ✅ (voir body PR #58).
- Limitation connue (non bloquante) : `hapticsEnabled` dans le DTO UserSettings partagé —
  pourrait ne pas persister au redémarrage si le backend strip les champs inconnus (backend hors scope).
- Build ✓ 0 erreur, Tests ✓ 533/0, Lint ✓ 0 erreur, Vérif visuelle ✓ 9 écrans non-blank.
- Qualité : /sonar skipped — api-mail non touché.

## Staging aggregation
- **Conflit best-effort → non agrégée** sur `forge/staging-task-142-160-20260716`.
- Cause : conflits `mail-list.component.{ts,spec.ts}` + `mail-detail.component.{ts,spec.ts}`
  (la staging porte task-149/152/153/154 qui ont touché ces mêmes fichiers ; task-160
  issue de `develop` sans elles). Merge annulé, PR #58 `feat → develop` intacte, task reste `done`.
- Note intégration humaine (HAG) : au merge, résoudre les conflits mail-list/mail-detail en
  combinant les changements des deux (polish UX task-160 + features task-149/152/153/154).

### Mise à jour agrégation (résolution manuelle à la demande humaine, 2026-07-16)
- task-160 **finalement agrégée** sur `forge/staging-task-142-160-20260716` (commit d01c736).
- Conflits mail-list/mail-detail (.ts + .spec.ts) résolus : union des imports (features 149/152/153/154
  + polish task-160), import `@ionic/angular` large conservé, doublon `of` retiré.
- Staging complète 142→160 : build ✓, **723 tests ✓ / 0 échec**.

## Merged
- 2026-07-17 — squash-merge sur `develop` (conflits imports mail-detail/mail-list combinés, specs union)
- `client-mobile` : fafaffa (PR #58 fermée)
