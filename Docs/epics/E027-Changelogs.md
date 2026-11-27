# E027 — Anneau de traitement : voir les boucles ouvertes — Changelogs

> **Audience** : équipes techniques (ingénierie, backlog, dette)
> **Vue produit** : [E027-anneau-de-traitement-voir-les-boucles-ou.md](E027-anneau-de-traitement-voir-les-boucles-ou.md)
> **Conception** : [`Docs/specs/anneau-de-traitement/`](../specs/anneau-de-traitement/specification.md) (spécification,
> maquettes variante D, revue de design — validées le 2026-11-27)
> **Dernière mise à jour** : 2026-11-27

---

## Historique détaillé des changelogs

### v0.1 — task-497 : l'anneau dans la liste et le détail (api-mail, dtos-mss, client-mobile, weda2)

- **État** : `done` — PRs en attente du merge humain (HAG). 3 reprises (1 sur revue, 1 sur décision humaine au HAG,
  1 sur la revue de cette décision).
- **PRs** : dtos-mss [#75](https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/75), api-mail
  [#382](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/382), client-mobile
  [#136](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/136) — label `awaiting-human-merge`.
  client-angular : commité par l'humain sur TFS, `feature/nova-mss-weda-integration` `2b991559` (56 fichiers). Ordre de
  merge : dtos-mss, api-mail, client-mobile ; weda2 avec eux.
- **Reprise 2 — décision humaine au HAG (2026-11-27)** : sur weda2, le bloc de l'anneau quitte `.mail-detail-reading`
  pour la section `ring` (« Traitement », icône `check-circle`) de `MailSidePanelComponent`, en premier ; présence par
  `hasRingSection` (= unités du bloc), pastille du rail, puce « Acquittement à traiter » rétablie, `requestedSidePanel`
  rétabli pour l'avis task-454 ; anneau du détail 72 → 56 px (panneau de 320 px). Catalogue (`3ad2b65b`) : textes de
  BIO-001 v3, BIO-003 v2, BIO-007 v2, DETAIL-004 v2 corrigés pour weda2, sans montée de version. Consigne
  `bloc-en-tete-de-lecture` (`conventions/angular.md`).
- **Reprise 3** (passage 4, B5) : l'avis consommait sa demande dans le tour du changement de message, puis le
  `resetKey` du panneau le repliait en lecture étroite. `RequestedSidePanel` porte désormais sa clé de message et n'est
  consommé qu'une fois ce message affiché et son contenu servi ; pastille du rail lue sur la ligne avant le chargement
  (S7). Consigne `demande-d-ouverture-liee-a-son-objet`. Passage 5 APPROVED ; suggestions N4 (demande en suspens), N5
  (ordre d'effets), N6 (`openSidePanelSection`).
- **Après les reprises** : /sonar et /lint-mobile en skip mesuré (aucun code concerné changé), /lint-angular 0 erreur,
  /e2e vert (mobile 84, angular 107), validation finale : api-mail 8 284 tests, mss-lib 2 167, weda2 2 683.
- **Contrat** : `HealthPlatform.Dtos.Mss` 635.0.0 → **638.0.0** (`6f00908`) — `MailDto.PendingBiologyAckStage` /
  `PendingBiologyAckLastAction`, `MailMedicalDocumentDto.BiologyAckHistory`, `MailBiologyAckProgressDto`,
  `UserSettingsDto.ListMarker` ; bump `api-mail` seul (avec ses `packages.lock.json`). `contract_impact.py check` :
  api-mcp, client-mobile, client-angular — aucun impact (un premier passage sortait en 2 : modèle mobile nommé
  `MailBiologyAckSummaryDto`, renommé `MailBiologyAckProgressDto`).
- **api-mail** (`bbb6d978`) :
  - règle pure `Domain/Rules/BiologyAckProgressRule.cs` : étape d'un compte rendu (aucune action → Reçu ; Pris
    connaissance ; rappel / convocation / adressage → Suite donnée ; Résolu ou antérieur au suivi → rien) ; le message
    suit le compte rendu le moins avancé, puis la dernière action la plus récente ;
  - appliquée dans `MailRepository.ApplyEnrichmentToMail`, dans la lecture groupée existante
    (`EnrichManyWithBiologyAcksAsync`) : **32 commandes SQL avant et après** sur la page de liste ;
  - historique des acquittements servi par `GET …/emails/content/{uid}` seulement, `null` sur les pages de liste et la
    vue par tag ;
  - évènement `MailBiologyAckChanged` après **tout** acquittement, intermédiaire compris, recalculé de la base,
    best-effort (une panne du relais ne fait pas échouer l'acquittement), aussi au rejeu de la file hors ligne ; sans
    auteur ni donnée de santé ;
  - aucune colonne « état d'anneau », aucune migration.
- **client-mobile** (`888f7cc`, `9ec2ddb`, `6f0e8f7`, reprise `06fb9b5`) : `treatment-ring.util.ts` (règle pure),
  `mss-treatment-ring` (SVG), `mss-treatment-ring-steps` (bloc du détail) ; ligne : anneau à la place de l'initiale,
  pastille d'initiales retirée, pastilles « Non affecté » / « Attente patient » / « Attente confrère », ⚠ atténué ;
  détail : boutons d'acquittement sous l'anneau, retirés de l'onglet Biologie ; réglage dans « Organisation » ;
  évènement en direct appliqué à la ligne et au détail ouvert.
- **weda2** (code-only) : `core/utils/mail-ring.util.ts`, `mail-ring-steps.util.ts`, `mail-ring-row.util.ts`,
  `ui/mail-ring/` (`mss-mail-ring`), `features/mail/components/mail-ring-panel/`,
  `features/mail/services/mail-biology-ack-live.service.ts` ; section d'acquittement retirée de
  `mail-side-panel` ; `biology-ack-panel` compacté (correctif DETAIL-004, voir E2E) ; réglage dans `mss-settings`.
- **Contraste** (spec du composant mobile) : étapes restantes `--app-outline` 4,49 à 3,67:1 ; anomalie `--app-flag`
  ≥ 4,84:1. weda2 : couleurs littérales dans `mail-ring.component.scss` (arbitrage A2).
- **Passe qualité `/simplify`** : client-mobile `9ec2ddb` (type de dossier mis en cache par chemin, tableau mort,
  gardes redondantes) ; weda2 3 fichiers (contexte de l'anneau calculé une fois par ligne) ; api-mail sans changement ;
  dtos-mss ignoré (porteur de contrat).
- **Revue** : anticipée passage 1 — backend APPROVED, clients CHANGES REQUESTED : B1 (mobile, `isHandled` testé avant
  `isToHandle` → anneau fermé sur un message à traiter), B2 (mobile et web, le patch en direct laissait la ligne
  « traitée » après une action postérieure à « Résolu »), B3 (mobile, la page renvoyait au détail sa copie périmée du
  message), B4 (web, parcours de l'arbre des dossiers et vue neuve à chaque rendu de chaque ligne), S1 (web, 4 segments
  avec les étapes du courrier), S2 (mobile, « Antérieur au suivi » déduit des compteurs au lieu de `isTracked`), S3
  (mobile, sous-dossier d'Envoyés avec anneau), S6 (mobile, « Masquer » cachait les boutons d'acquittement) ; reprise
  1 ; passage 2 APPROVED ; validation finale sans diff depuis l'approbation.
- **Arbitrages humains ouverts** (recopiés en PR) : A1 « reste : … » dans tous les libellés accessibles (exemple 2 de
  la règle 8) ; A2 couleurs littérales du SCSS weda2 contre les jetons `--ds-*` ; A3 compte rendu résolu : anneau
  fermé sur mobile, étapes seules sur web, coche animée sur mobile seulement.
- **Tests** :
  - unitaires api-mail `BiologyAckProgressRuleTests` (20 : les 9 cas de la DoD, départage, gravité ; 9 mutations
    rouges) ;
  - intégration (règle 1b) : `TheListRow_SaysTheAcknowledgementStage…` ×3 (dossier, tag, hors ligne — code d'avant :
    `Expected (1, Received, null) Actual (1, null, null)`), `TheListRow_CarriesTheStageAsAnInteger…` (sans anomalie →
    400), `TwoReportsInOneMessage…`, `AnAcknowledgementOnAMessageOfAPastFolderGeneration…`,
    `TheListPage_ServesTheStage_WithoutOneMoreSqlCommand` (32 = 32, rouge si l'historique est lu sur les listes),
    `ReadingOneMessage_ServesTheAcknowledgementHistory…` (4 mutations), `TheDelegateAcknowledges_…` (règle 14 :
    titulaire relit l'étape, trace au nom du délégataire, évènement livré — 3 mutations), `TheListMarker_…`,
    `BiologyAckServiceLiveProgressTests` (6 mutations) ;
  - mobile : 120 mutations unitaires, 118 rouges sur l'assertion visée, 2 sans effet observable (U15, C13) ; reprise :
    mutations B1 à S6 ;
  - weda2 : 83 mutations unitaires, toutes rouges ; reprise : 11 mutations B4 (1 équivalente survit), 6 B2, 3 S1 ;
  - suites : api-mail domain 388, infrastructure 749, application 4 373, api 1 388, intégration 1 386 (+16 ignorés),
    0 échec, build 0 avertissement ; mobile **1 933 / 1 933** ; `nx test mss-lib` **2 160 / 2 160**, `nx test weda2`
    **2 683 / 2 683**, `nx build weda2` OK.
- **Sonar** (api-mail `bbb6d978`) : QG OK, new coverage 95,9 → **96,1 %** (lignes 98,3 %, branches 90,6 %), 0 bug /
  vulnérabilité / hotspot / smell, couverture projet 97,6 %, duplication 0,3 %, A/A/A ; aucun commit. Conditions non
  couvertes : 2 dans `BiologyAckProgressRule.Leader.Leads`, 1 dans `MailRepository.ToBiologyAckDto`.
- **Lint** : weda2 0 erreur (41 warnings préexistants, aucun sur une ligne ajoutée), aucun fichier modifié ; mobile
  « All files pass linting ».
- **E2E** :
  - catalogue : ajoutés v1 **E2E-RING-001**, **E2E-RING-002**, **E2E-RING-003**, **E2E-SETTINGS-005** ; montés
    E2E-ASSIGN-001 2 → 3, E2E-BIO-001 2 → 3, E2E-BIO-003 1 → 2, E2E-BIO-007 1 → 2, E2E-DETAIL-004 1 → 2 (angular) ;
    E2E-BIO-004 adapté sans changer de version ;
  - preuves par mutation : mobile M1 à M7b ; weda2 8 mutations (recompilation prouvée par un marqueur dans le bundle
    servi) ;
  - DETAIL-004 rouge sur un vrai défaut weda2 : à 1366×768 le bloc de l'anneau défilait en interne et coupait
    « Marquer comme résolu » ; `biology-ack-panel` compacté, plafond du bloc à 75 %, 265 px sans défilement interne ;
    DETAIL-004 v2 affirme le bouton dans la vue (`toBeInViewport({ ratio: 1 })`) ;
  - `/e2e` : mobile **84 verts**, angular **107 verts**, 0 flaky, 0 rouge, quarantaine E2E-COMPOSE-002 (angular),
    parité verte, porte code 0.
- **Prévention** : `conventions/angular.md`, entrées `drapeaux-serveur-combinables` et
  `page-hote-ne-renvoie-pas-sa-copie`.
- **Ouvert** :
  - DoD « références Stitch `mail-list` et `mail-detail` mises à jour » non faite (écrans d'avant l'anneau ; laissée à
    l'humain) ;
  - mobile : l'anneau remplace aussi l'avatar vert des messages de patient (le tag « Patient » reste) ; après un
    acquittement, la ligne est relue du serveur en plus de l'évènement ;
  - hors ligne, le contenu d'un message ne porte pas ses documents : pas d'historique d'acquittement hors ligne
    (antérieur à la task) ;
  - suggestions de revue N1 (mobile, `mail-detail.page.ts` renvoie encore sa copie sur `mailUpdated$` /
    `emailsEnriched$`, défaut antérieur), N2 (web, `refreshRing` peut écraser `isRead` / `assignment` par une réponse
    périmée et pose `handling` hors `MailHandlingService.apply`), N3 (web pose `isToHandle`, mobile s'en remet à la
    règle) ; backend : collecte unique ligne / évènement, test de composition du relais, `ThenBy(Id)` sur
    l'historique ; pas de parcours e2e en direct à deux personnes avec une action après « Résolu » (aurait attrapé
    B2) ;
  - taille : PR mobile ≈ 52 fichiers, au-delà du repère d'environ 30.
- **Cycle** : 1 h 18 min (dont `/e2e` 30 min, `/develop` 22 min 31 s, `/sonar` 15 min 44 s).

---

## Annexe A — Cartographie des briques applicatives

| Brique | Rôle | Task |
|---|---|---|
| `api-mail/src/Domain/Rules/BiologyAckProgressRule.cs` | étape d'acquittement d'un compte rendu et d'un message | task-497 |
| `api-mail` `MailRepository.ApplyEnrichmentToMail`, `EnrichManyWithBiologyAcksAsync` | étape servie sur la ligne, sans requête de plus | task-497 |
| `api-mail` `MailRepository.ToBiologyAckDto`, `GET …/emails/content/{uid}` | historique des acquittements du détail | task-497 |
| `api-mail` évènement `MailBiologyAckChanged` (`BiologyAckService`) | mise à jour en direct après tout acquittement | task-497 |
| `dtos-mss` `MailDto.PendingBiologyAckStage` / `PendingBiologyAckLastAction`, `MailMedicalDocumentDto.BiologyAckHistory`, `MailBiologyAckProgressDto`, `UserSettingsDto.ListMarker` | contrat de l'anneau (638.0.0) | task-497 |
| client-mobile `core/utils/treatment-ring.util.ts`, `mss-treatment-ring`, `mss-treatment-ring-steps` | règle, anneau, bloc du détail mobile | task-497 |
| weda2 `libs/mss/src/core/utils/mail-ring.util.ts`, `mail-ring-steps.util.ts`, `mail-ring-row.util.ts` | règle, étapes, mémoire de ligne web | task-497 |
| weda2 `libs/mss/src/ui/mail-ring/`, `features/mail/components/mail-ring-panel/` | anneau et bloc du détail web | task-497 |
| weda2 `features/mail/services/mail-biology-ack-live.service.ts`, `MailStateService.ringFolderTypes` | direct et type de dossier mis en cache | task-497 |
| `Api/Mail/e2e/scenarios.yml` E2E-RING-001/002/003, E2E-SETTINGS-005 | parcours de l'anneau | task-497 |

---

## Annexe B — Inventaire fonctionnel daté (2026-11-27)

- Tasks de l'EPIC : 3 — 1 `done` (497), 2 `todo` (498, 499).
- Scénarios e2e de l'EPIC au catalogue : 4 ajoutés (E2E-RING-001, E2E-RING-002, E2E-RING-003, E2E-SETTINGS-005) ;
  5 montés de version (E2E-ASSIGN-001 v3, E2E-BIO-001 v3, E2E-BIO-003 v2, E2E-BIO-007 v2, E2E-DETAIL-004 v2).
- Prévus au backlog : E2E-RING-004, E2E-SETTINGS-006 (task-498), E2E-DASH-002 (task-499).

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Contribution | État |
|---|---|---|
| task-497 | L'anneau dans la liste et le détail : étape d'acquittement servie sur la ligne sans requête de plus, historique daté dans le détail, évènement en direct pour tout acquittement, anneau et bloc du détail sur les deux clients, initiales dans l'anneau, « Non affecté » / « Attente patient » / « Attente confrère », boutons d'acquittement sous l'anneau (section « Traitement » du panneau latéral sur weda2), préférence anneau / icône classique | `done` (PRs #75, #382, #136) |
| task-498 | Ancienneté : seuils par catégorie réglés au niveau de la boîte (changement tracé), compteur J+N / H+N calculé sur le poste, préférences d'affichage, contraste renforcé, légende | `todo` |
| task-499 | Tableau de bord : « dont N en retard » sur les tuiles existantes, tuile « Non affectées », listes filtrées servies par le serveur, après mesure sur une boîte de 10 000 messages | `todo` |
| task-500 | Ligne de liste allégée : « Non affecté » et identifiant hors de la ligne (survol de l'anneau), compteur de conversation en pastille grise sur l'anneau, icône « répondu » au bord de l'anneau, 2 valeurs de biologie au plus, une seule date, moins de puces redondantes (weda2 et mobile) | `todo` |
