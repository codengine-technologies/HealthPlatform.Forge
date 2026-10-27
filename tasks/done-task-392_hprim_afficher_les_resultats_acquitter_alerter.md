# todo-task-392.md — Résultats HPRIM : l'anomalie est celle du biologiste, le partiel se voit, le texte est lisible

**Repos**: api-mail, client-mobile, client-angular
**Dependencies**: task-390 (résultats structurés, statut)
**Epic**: E009
**Priorité**: **2** — depuis task-390, une valeur HPRIM hors de ses bornes sans indicateur du laboratoire est signalée comme anomalie : elle entre dans la file « à acquitter » et dans « anormaux non lus », alors que le biologiste ne l'a pas jugée anormale. Le même examen reçu en CDA ne le serait pas. Le statut « partiel » n'est visible nulle part, et le texte du compte rendu montre les lignes techniques du laboratoire.

> **Origine.** Séance `/po` du 2026-10-23 (parsing HPRIM), suite de task-389 et task-390.
> Arbitrages rendus le 2026-10-26 (voir « Décisions actées »).
>
> **Révision de la décision 1 de task-390** (humain, 2026-10-26).
> - task-390 avait retenu : « indicateur du laboratoire, sinon valeur hors de ses bornes ». La règle s'inspirait de Weda, mais Weda n'en fait qu'un **style d'affichage**, rouge, activé par une préférence de l'utilisateur (`userPreferenceHprim.Anormale`). Ni alerte, ni acquittement.
> - Décision : **le jugement d'anomalie appartient au biologiste.** Seul l'indicateur du laboratoire fait l'anomalie, exactement comme le code d'interprétation d'un CR-BIO CDA.
>
> **Pas de remplacement du partiel** : task-391 a été réduite au signal doublon. Le partiel et son complété restent tous deux visibles ; le partiel se reconnaît à sa mention « partiel ».

## Ce qui est établi

- **CDA** (`CdaParsingService`) : un résultat est signalé **seulement** si le laboratoire a posé un code d'interprétation `L`, `H`, `A`, `LL`, `HH` ou `AA`. L'intervalle de référence est affiché, jamais comparé à la valeur. Les clients colorent une ligne d'après ce code (critique, anormal, flèche ↑ ↓).
- **HPRIM depuis task-390** (`HprimStructuredResults`) : un résultat est signalé si l'indicateur du laboratoire (champ 8) est l'un de ces codes. **Sinon**, il est signalé dès qu'une valeur numérique sort de ses bornes. Cette seconde branche fait entrer le document dans la file « à acquitter » (task-170) et compte le patient dans « anormaux non lus ». Les clients, eux, n'affichent pas d'anomalie sans code : le médecin voit un document « à acquitter » sans valeur anormale visible.
- Le champ 8 d'une ligne `RES|` est l'**équivalent exact** du code d'interprétation CDA : même table HL7 (N, L, H, LL, HH, A, AA).
- **Statut** (task-390) : P partiel, F final, C corrigé, persisté et exposé ; aucun client ne l'affiche.
- **Texte du document HPRIM** : il contient encore le bloc technique du laboratoire (`****LAB****`, lignes `TEX|` et `RES|`).
- **Frise de biologie du patient** (mobile et weda2, `biology-timeline`) : les courbes se forment par section, puis par code + libellé + unité.
  - Tous les résultats HPRIM sont dans la section « Résultats de laboratoire ». Un CR-BIO CDA porte en pratique ses propres sections (Biochimie, Hématologie…) : un HPRIM et un CDA ne partagent pas de courbe.
  - **Aucun changement dans cette US** (humain, 2026-10-26) : une courbe par laboratoire couperait l'historique d'un patient qui change de laboratoire, pour un risque de fusion à tort très faible (même code, même libellé et même unité pour deux examens différents).
- **Tableau de biologie du détail** (mobile et weda2) : il affiche déjà les résultats HPRIM (valeur, unité, bornes), avec le même composant que le CR-BIO CDA.

## Décisions actées (humain, 2026-10-26)

1. **Anomalie = indicateur du laboratoire, seulement.** Une valeur hors de ses bornes sans indicateur n'est **pas** une anomalie : ni mise en évidence, ni acquittement, ni « anormaux non lus ». La valeur et ses bornes restent affichées côte à côte : le médecin voit l'écart et en juge. Le HPRIM se comporte exactement comme le CDA.
2. **Détail d'un document HPRIM** :
   - le **tableau des résultats** d'abord : valeur, unité, bornes, anomalie du laboratoire mise en évidence, mention « partiel » ;
   - **puis le texte** du compte rendu, sans les lignes techniques ;
   - le PDF reste accessible comme pour un CDA.
3. **Acquittement** : comme un CR-BIO CDA. Un document HPRIM entre dans la file « à acquitter » quand le **laboratoire** a signalé au moins une valeur.
4. **Hors périmètre** :
   - un repère visuel neutre « hors intervalle de référence » (le rouge de Weda) n'est pas livré. S'il est demandé, ce sera une **préférence de l'utilisateur**, dans une US à part ;
   - les courbes de la frise ne changent pas (pas de courbe par laboratoire). Un cas réel de fusion à tort sera traité avec l'exemple sous les yeux.

## Objective

Le médecin lit un résultat HPRIM comme un CR-BIO CDA :
- seules les anomalies posées par le biologiste sont signalées, mises en évidence et à acquitter ;
- le résultat partiel est reconnaissable ;
- le texte est lisible.

### Règles métier

- **Anomalie** (décision 1) : un résultat HPRIM est signalé si, et seulement si, son indicateur vaut `L`, `H`, `A`, `LL`, `HH` ou `AA`. Les bornes ne font jamais une anomalie.
  - **`N`, vide ou inconnu** (`*`, `+`…) : le résultat n'est pas signalé.
  - **Mise en évidence** : identique au CDA (critique, anormal, flèche).
- **Tableau des résultats** (détail du document, mobile et weda2) : une ligne par résultat, avec libellé, valeur, unité, bornes et seconde valeur si elle existe.
  - **« Partiel »** sur chaque résultat partiel, et en tête du document s'il en porte au moins un.
  - **Le code local du laboratoire** n'est jamais présenté comme un code LOINC (libellé « code labo »).
- **Texte du compte rendu** : affiché sous le tableau, tel que le laboratoire l'a mis en forme, sans les lignes techniques. Un HPRIM sans résultat structuré n'affiche que son texte.
- **Frise du patient** : courbes inchangées ; un point « partiel » est marqué.
- **« Anormaux non lus » et acquittement** : règles existantes du CDA, inchangées. Seul l'indicateur du laboratoire y fait entrer un résultat HPRIM.
- **Partiel et complété** : tous deux visibles et acquittables ; aucun remplacement.
- **BAL déléguée** (règle 14) :
  - le tableau et le texte d'un HPRIM délégué s'affichent de la même façon, lus en direct à l'ouverture du message ;
  - pas d'acquittement, ni d'entrée dans « anormaux non lus » ou dans la frise (task-398 inchangé) ;
  - rien n'est persisté chez le délégataire.

## Definition of Done

- [ ] Build et tests verts : api-mail, client-mobile, client-angular
- [ ] **Anomalie (api-mail)** : la comparaison aux bornes est retirée de la lecture `RES|`. Les tests unitaires de task-390 qui la portaient sont remplacés :
  - indicateur `L`/`H`/`A`/`LL`/`HH`/`AA` → signalé ;
  - `N`, vide ou inconnu → non signalé, même hors bornes
- [ ] **Test d'intégration (règle 1b)**. Un HPRIM rattaché porte deux valeurs : une hors bornes sans indicateur, une signalée `H` par le laboratoire.
  - **Pour `GET biology/patients/{id}`** : seule la valeur `H` porte `IsFlagged`, lu dans la réponse réelle.
  - **Pour `GET biology/abnormal-unread`** : le patient y figure avec la seule valeur `H`.
  - **Cas d'échec** : un HPRIM dont toutes les valeurs sont hors bornes sans indicateur → le patient n'est pas dans « anormaux non lus », et le document n'est pas dans la file « à acquitter ».
  - Vu rouge sur le code de task-390.
- [ ] **Test d'intégration (règle 1b) pour le contenu d'un message HPRIM** : le texte du document ne contient plus les lignes `****LAB****`, `TEX|`, `RES|`, et garde le texte du compte rendu ; vu rouge
- [ ] Tests de composant (mobile et weda2) :
  - tableau des résultats HPRIM : valeur `H` mise en évidence comme un CDA ; valeur hors bornes sans indicateur **non** mise en évidence ; mention « partiel » ; seconde valeur ; « code labo » ;
  - frise : un point « partiel » est marqué
- [ ] Scénario **E2E-BIO-003** ajouté dans Api/Mail/e2e/scenarios.yml (version 1), requis sur mobile et angular, implémenté dans les deux clients. Seed e2e d'un HPRIM synthétique avec une valeur signalée `H` par le laboratoire, une valeur hors bornes sans indicateur et un résultat partiel. Attendu : « ouvrir un résultat HPRIM ; seule la valeur signalée par le laboratoire est mise en évidence ; la mention partiel est visible ; l'acquitter »
- [ ] **BAL déléguée — test d'intégration** (banc de délégation de task-397) :
  - le détail d'un HPRIM délégué renvoie un texte sans lignes techniques, et seules les valeurs signalées par le laboratoire portent `IsFlagged` ;
  - « anormaux non lus » du délégataire reste vide ;
  - la base du délégataire ne contient aucune ligne pour ce message ;
  - vu rouge (règle 1b)
- [ ] La doc d'EPIC E009 corrige la règle d'anomalie de task-390 (v1.113) : l'anomalie est celle du biologiste
- [ ] Aucune donnée de santé en clair dans les journaux (valeurs, libellés, traits patient)
- [ ] data-testid sur tout élément interactif ajouté ; aucune chaîne en dur (i18n)

## Manual Test Plan

Lancer l'AppHost, puis le mobile (`cd Client/Mobile && npm start`) et weda2. Se connecter en Cyril par PSC.
Messages de test : HPRIM synthétiques (`.eml` déposés dans la Réception de Cyril), dont un avec :
- une valeur hors bornes **sans** indicateur ;
- une valeur signalée « H » par le laboratoire ;
- une valeur qualitative ;
- un résultat partiel.

1. Ouvrir le message :
   - le tableau vient en tête, et **seule** la valeur « H » est mise en évidence (flèche ↑, comme un CR-BIO CDA) ;
   - la valeur hors bornes sans indicateur s'affiche normalement, avec ses bornes à côté ;
   - le résultat partiel porte « partiel », en tête du document aussi ;
   - le code est présenté comme « code labo ».
2. Sous le tableau, le texte du compte rendu s'affiche **sans** les lignes `****LAB****`, `TEX|`, `RES|`. Le PDF reste accessible.
3. Le document est dans la file « à acquitter » (à cause de la valeur « H ») ; l'acquitter.
4. Un second HPRIM dont les seules valeurs anormales sont hors bornes **sans** indicateur : il n'est **pas** dans la file « à acquitter », et une fois rattaché, son patient n'est pas dans « anormaux non lus ».
5. Rattacher le premier document à une fiche : le patient apparaît dans « anormaux non lus » avec la valeur « H ».
6. Frise de biologie du patient : le point du résultat partiel est marqué « partiel ».
7. **BAL déléguée** : ouvrir le même HPRIM dans la boîte de Virginie, en Cyril. Le tableau et le texte s'affichent, sans acquittement ; « anormaux non lus » de Cyril reste vide.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : biologie médicale (réception en médecine de ville)
- **Vague Ségur** : hors Ségur — HPRIM est un format historique ; le CR-BIO CDA reste prioritaire
- **Exigences DSR honorées** : non applicable — aucune exigence DSR sur le HPRIM.
  - Règles de prudence : l'anomalie est celle validée par le biologiste, jamais déduite par la plateforme.
  - Codes locaux jamais présentés comme LOINC ; une courbe HPRIM n'est jamais mêlée à une courbe LOINC (sections distinctes).
- **INS** : non applicable — aucun changement d'identité ; « anormaux non lus » ne porte que sur les documents rattachés (task-390)
- **Authentification PS** : inchangée — PSC / e-CPS de la session de messagerie
- **Habilitations** : inchangées. BAL déléguée : lecture seule sans stockage, sans acquittement (règle 14, task-398)
- **Interop CI-SIS** : non applicable — HPRIM Santé ; indicateur d'anomalie sur la table HL7 commune avec le CDA (ObservationInterpretation)
- **Tracé PGSSI-S** : l'acquittement suit le tracé existant (task-170) ; aucun nouvel évènement
- **Consentement patient** : non applicable — aucun envoi vers le DMP ni Mon Espace Santé
- **Référentiels métier** : codes d'examen locaux au laboratoire (ni LOINC ni NABM) ; indicateurs HL7 (N, L, H, LL, HH, A, AA)
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangée — affichage de données déjà reçues et conservées

## Branches
- `api-mail` (pushed) : feat/task-392-hprim-afficher-les-resultats-acquitter — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-392-hprim-afficher-les-resultats-acquitter
- `client-mobile` (pushed) : feat/task-392-hprim-afficher-les-resultats-acquitter — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-392-hprim-afficher-les-resultats-acquitter
- `client-angular` (code-only) : la forge écrit le code sur la branche actuellement checked out dans `Client/Angular/` (`feature/nova-mss-weda-integration` au /start) — humain gère branche, commit, push, PR TFS
- Run `/forge` `forge-20261026-391-392` (staging `forge/staging-task-391-392-20261026`)

## Timings

*(généré par `tools/timing/report.sh --task task-392 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 8.1 s | — | — | — | — |
| /develop | ok | 28 min 06 s | 8 (1 min 21 s) | 9 (7 min 23 s) | — | api-mail 4B/5T, client-mobile 3B/3T, client-angular 1B/1T |
| /sonar | ok | 9 min 06 s | 1 (43 s) | 5 (6 min 42 s) | 2 (44 s) | 1 itération(s), api-mail 1B/5T |
| /lint-angular | ok | 22 s | — | — | — | — |
| /lint-mobile | ok | 12 s | — | — | — | — |
| /e2e | ok | 50 min 27 s | — | — | — | e2e ×17 (2 h 03 min) |
| /review | ok | 26 min 31 s | 4 (41 s) | 4 (5 min 24 s) | — | api-mail 2B/2T, client-mobile 1B/1T, client-angular 1B/1T |
| **Total cycle** | | **1 h 54 min** | **13 (2 min 46 s)** | **18 (19 min 29 s)** | **2 (44 s)** | |

Autres commandes mesurées : lint ×2 (17 s)

## Develop log

> Journal de progression (point de reprise en cas de compaction).

- **Repos touchés** : `api-mail`, `client-mobile` et `client-angular` (code seul). Aucun contrat `dtos-mss` changé : `Status`, `CodeSystem` et `IsFlagged` existent depuis task-390.

### api-mail

- **Anomalie = l'indicateur du laboratoire, seul** (décision 1, option 1 de l'humain).
  - `HprimStructuredResults.FromLine` pose `IsFlagged = BiologyInterpretation.IsFlaggedCode(InterpretationCode)`, exactement comme le CDA.
  - Retirés : la comparaison aux bornes, le type `N`, les bornes `0|0` et le repli des indicateurs inconnus.
  - L'indicateur en minuscules (« h ») reste lu, car il est mis en majuscules.
  - Conséquence : un document dont aucune valeur n'est signalée par le laboratoire n'entre ni dans la file « à acquitter », ni dans « anormaux non lus ».
- **Texte lisible** : `HprimStructuredResults.WithoutTechnicalLines` retire `****LAB****` et les lignes `TEX|` et `RES|` du texte du document. `HprimMedicalDocuments` l'applique au `Body` ; les résultats structurés restent lus sur le texte complet.
- **Jeu e2e** : nouvelle donnée `cr-bio-hprim` (message **lu**, 59 min, juste avant le plus ancien), avec `E2eAttachmentKind.Hprim` (`resultat.hpm`). Le patient est fictif (« HPRIME2E Camille »). Il porte une glycémie hors bornes sans indicateur, un potassium « H » et une créatinine partielle.
  - ~~Aucun scénario existant n'affirme un nombre de comptes rendus à acquitter.~~ **Faux, corrigé** : E2E-BIO-001 côté weda2 lisait « (1) » sur la puce des comptes rendus à acquitter ; le HPRIM (potassium « H ») en fait 2. Le spec weda2 attend désormais « (2) ». La vérification avait porté sur le mobile seulement.
  - E2E-BIO-001 acquitte le plus récent, qui reste le CR-BIO CDA.
- **Catalogue** : E2E-BIO-003 v1, requis sur mobile et angular, origine task-392. `ScenarioCatalogTests` est vert.

**Tests et preuves** :
- **Unitaires** (`HprimStructuredResultsTests`), section anomalie réécrite :
  - indicateurs L/H/A/LL/HH/AA → signalé ;
  - hors bornes sans indicateur (point ou virgule) → non signalé ;
  - indicateur N, vide ou inconnu → non signalé, même hors bornes ;
  - seconde valeur hors bornes → non signalée ;
  - indicateur en minuscules → lu ;
  - texte sans lignes techniques ;
  - document : texte nettoyé, résultats gardés.
- **Intégration (règle 1b)** : `HprimStructuredResultsEndToEndTests`.
  - **nominal** mis à jour : la glycémie hors bornes sans indicateur n'est plus signalée ; « anormaux non lus » compte 1 (le potassium « H ») ; le statut de l'en-tête est lu sur le potassium.
  - **nouveaux** :
    - `AnHprimOutOfItsNormsWithoutLaboratoryIndicator_IsNeitherAnAnomalyNorToAcknowledge` : biologie non signalée, « anormaux non lus » vide, absent de `GET biology-acks/pending-mail-uids` ;
    - `AnHprimFlaggedByTheLaboratory_IsToAcknowledge` : prémisse, la file répond ;
    - `TheHprimText_IsServedWithoutItsTechnicalLines`.
  - La file « à acquitter » est composée dans le harnais par ses constructeurs de production (`BiologyAckRepository`, `BiologyAckService`).
- **BAL déléguée** : `ADelegatedHprimWithResLines_…` a désormais une valeur signalée « H » par le laboratoire, et affirme un texte délégué sans lignes `RES|`.
- **Rouge par mutation** :

  | # | Mutation | Tests rouges |
  |---|---|---|
  | MN | des bornes font l'anomalie (`… || PrimaryMaxValue.Length > 0`) | hors bornes sans indicateur, nominal, « anormaux non lus » |
  | MT | texte non nettoyé | texte sans lignes techniques, BAL déléguée |

- **Suites** : api-mail vert hors fenêtre de minuit (integration 1024/1042 : 2 rouges `ImapFolderServiceIntegrationTests` « du jour », connus entre 00:00 et 02:00, sans lien ; 16 skipped).
- **Commits** : `6f91a8b0` (feature), `8a701913` (passe qualité). Poussé.

**Passe qualité §Q (api-mail)** — 4 relectures (réutilisation, simplification, efficacité, altitude) :
- appliqué : `UseCaseHttpHost.AddProductionBiologyAcks` (au lieu d'un enregistrement DI à la main) ; les tests citent `LinePrefix` / `TextLinePrefix` / `LabBlockMarker` ; retrait de cas vestiges de la comparaison aux bornes (« 1,45 », indicateur vide en double, `IsFlagged` redondant) ;
- écarté : fusion des deux découpes de `result.Text` (gain négligeable, couplerait deux fonctions testées séparément) ; paramètre `type` de `HprimSamples.ResLine` (champ du format, gardé) ;
- altitude : règle d'anomalie unique avec le CDA (`BiologyInterpretation.IsFlaggedCode`), nettoyage au service — rien à changer ;
- re-validation : build 0 warning, tests HPRIM + délégation 153/153 verts.

### client-mobile

- **Biologie (`mss-biology`)** : « partiel » sur chaque ligne de statut P (`biology-partial-{id}`) et bandeau en tête du document (`biology-document-partial`) ; « code labo X » pour un code `LABORATORY-LOCAL` (`biology-lab-code-{id}`), jamais présenté comme un LOINC ; seconde valeur et ses bornes (`biology-secondary-{id}`). La surbrillance reste l'indicateur du laboratoire (`isFlagged`), rien d'autre.
- **Onglet document HPRIM** (`mail-body`) : un HPRIM n'a pas de HTML et affichait « Aucun contenu structuré ». Il montre maintenant le tableau de ses résultats, puis son texte (`doc-body-hprim`).
- **Frise biologie du patient** : un point P porte la classe `bio-value-partial`, la mention « partiel » et « Résultat partiel » dans son infobulle.
- **E2E-BIO-003 v1** dans `e2e/specs/functional.spec.ts` : message trouvé par son UID serveur ; glycémie hors bornes **non** surlignée, potassium « H » surligné, créatinine « partiel », texte sans `RES|`/`TEX|`/`****LAB****` ; acquittement : « À TRAITER » lu avant, `POST …/biology-ack` exigé `ok()`, état relu après rechargement. Sauté en mode humain seulement (`test.skip(!HEADLESS)`).
- **Tests de composant** : 9 nouveaux, vus rouges par neutralisation des fonctionnalités puis restaurés.
- **Vérifié par la forge** : build vert (avertissement de budget scss sur `biology.component.scss`, 2,64 ko pour 2 ko, comme 6 autres composants), tests 1346/1346, `tsc -p e2e` vert.
- **Commits** : `6f3712b` (feature), `6636430` (passe qualité). Poussé.

**Passe qualité §Q (client-mobile)** :
- appliqué : `HPRIM_FORMAT` déplacé dans `core/models/mail.model.ts` ; E2E-BIO-001 réutilise `biologyAckCall` (prédicat strict sur le chemin) ; une seule lecture des résultats par document, `isPartial = isPartialBiologyResult` ;
- écarté : fusion des branches « PDF externe » de l'onglet document (changerait l'affichage d'un HPRIM sans texte) ; `@let` pour les appels doublés du gabarit (composant OnPush, coût négligeable) ;
- re-validation : build, tests 1346/1346, `tsc -p e2e` verts.
- **Point de vigilance pour /e2e** : le message HPRIM porte un « H » et sera épinglé dans « Biologie à valider » en tête de boîte ; la voie mobile entière doit être rejouée (gestes de `mail-non-lu`, E2E-AI-001).

### client-angular (code seul, branche `feature/nova-mss-weda-integration`, rien commité)

- **Biologie (`mss-biology`)** : « partiel » sur la ligne (`biology-partial-{id}`) et en tête du document (`biology-document-partial`) ; « code labo X » (`biology-lab-code-{id}`) ; seconde valeur (`biology-secondary-{id}`). Mêmes `data-testid` que le mobile.
- **`mss-biology-value`** : une valeur hors bornes **sans** indicateur du laboratoire prend la classe `neutral` (elle était colorée par les bornes, en rouge pulsé pour la glycémie). L'anomalie = `isCritical` (le `IsFlagged` du serveur) ou un code HL7 d'anomalie (`isLaboratoryFlagCode` : L, H, A, LL, HH, AA, comme `BiologyInterpretation.IsFlaggedCode`). **S'applique aussi au CDA** — c'est la décision 1 (« le jugement d'anomalie appartient au biologiste »), à voir au HAG.
- **Onglet à l'ouverture** (`mail-body`) : un mail dont tous les documents sont des HPRIM structurés s'ouvre sur l'onglet Biologie (décision 2 : le tableau d'abord) ; le texte reste dans l'onglet du document.
- **Frise** : le point partiel porte `bio-value-partial` (« partiel ») et « Résultat partiel » dans l'infobulle.
- **Utilitaire** `core/utils/biology-result.util.ts` : `isPartialResult`, `isLaboratoryLocalCode`, `isLaboratoryFlagCode`, `isHprimDocument`.
- **E2E** : E2E-BIO-003 v1 dans `e2e/mss-e2e/specs/functional.e2e.ts` (message retrouvé par son UID serveur, cf. `ligne-de-cda`) ; **E2E-BIO-001 attend « (2) »** sur la puce des comptes rendus à acquitter (le HPRIM « H » y entre) — voir la convention `seed-partage-des-deux-clients`, créée à cette occasion.
- **Specs de composant** : `biology.component.hprim.spec.ts`, `mail-body.component.hprim.spec.ts`, `biology-timeline.component.partial.spec.ts`, vus rouges par mutation.

**Passe qualité §Q (client-angular, sans git)** :
- appliqué : BIO-001 réutilise `biologyAckCall` ; `isHprimDocument` et `HPRIM_FORMAT` dans l'utilitaire (plus de littéral `'HPRIM'` dans `mail-body`) ; un `computed` unique pour le code normalisé dans `biology-value` ;
- **correction trouvée en passant** : `isFlagged` comptait tout code autre que « N » comme une anomalie (« * », « + »…), contrairement au serveur. Liste blanche HL7 ; test `ne met pas en évidence une valeur hors bornes dont l'indicateur n'est pas un code HL7 d'anomalie`, **vu rouge** avant la correction, vert après ;
- écarté : extraction d'un `acknowledgeBiology(page)` commun BIO-001/BIO-003 et d'un `mailRowByUid` (gain faible, specs e2e non rejoués avant /e2e) ; pré-calcul de `partial`/`labCode`/`secondary` dans `BiologyRow` (OnPush, gain de cohérence seulement) ;
- re-validation : `npm run build` vert, `nx run-many -t test --projects=tag:scope:mss` 124 fichiers verts, `tsc -p e2e/mss-e2e` vert, lint `tag:scope:mss` 0 erreur (2 erreurs introduites par la passe, corrigées : jsdoc déplacé, prettier).

### Écarts au playbook

- **E2E-BIO-003 n'a pas été joué sur le banc `--serve-only` en /develop** (consigne `selecteur-de-controle-de-formulaire`, Step 6b.3) : les deux agents clients n'en avaient pas la consigne dans leur brief. /e2e le jouera ; un rouge de sélecteur y est probable. Leçon pour l'orchestrateur : un brief de sous-agent qui écrit un test e2e cite la Step 6b.3.

### DoD — auto-contrôle /develop

- [x] Build et tests verts : api-mail (hors 2 tests « du jour » de la fenêtre de minuit, sans lien), client-mobile 1346/1346, client-angular mss 124 fichiers.
- [x] Anomalie api-mail : comparaison aux bornes retirée, tests unitaires remplacés.
- [x] Intégration règle 1b (biologie, anormaux non lus, file à acquitter, cas d'échec) — vus rouges par mutation MN.
- [x] Intégration texte sans lignes techniques — vu rouge par mutation MT.
- [x] Tests de composant mobile et weda2 (H mis en évidence, hors bornes sans indicateur non, partiel, seconde valeur, code labo, frise partielle).
- [x] E2E-BIO-003 v1 au catalogue, requis mobile + angular, implémenté dans les deux clients ; seed HPRIM synthétique. **Joué par /e2e.**
- [x] BAL déléguée : test d'intégration mis à jour (valeur « H », texte sans `RES|`), vu rouge (MT).
- [ ] Doc E009 — par /tech-writer.
- [x] Aucune donnée de santé dans les journaux : aucun journal ajouté.
- [x] `data-testid` sur les éléments ajoutés. Chaînes : ces composants (biologie, frise) n'utilisent pas d'i18n sur aucun des deux clients ; les libellés ajoutés suivent l'existant.

## Sonar log

Analyse complète `healthplatform-api-mail` (SonarQube 9.9.8 local, `sonar.login`), sur `feat/task-392-…` à `8a701913`.

- **Analyse** : **QG OK, 0 issue** sur le nouveau code, aucun hotspot, new coverage 95,1 %. Suites : domain 264, application 3 785, infrastructure 701, api 1 347 vertes ; integration 1 023/1 042, **3 rouges « du jour »** (`ImapFolderServiceIntegrationTests` ×2, `EmailReadingUseCaseTests.FilterTodayEmails…`) : analyse lancée à 00:20, fenêtre de minuit connue, sans lien avec la task.
- **Phase 1 (nouveau code)** : rien à corriger.
- **Phase 2 (legacy)** : rien à faire (0 bug, 0 vulnérabilité, 0 smell sur le projet).

### KPIs qualité (baseline → final)

| Métrique | Baseline (`3ef5617c`, task-391) | Final (`8a701913`) | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | = |
| New coverage | 95,1 % | 95,1 % | = |
| New bugs / vulnérabilités / smells | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Bugs / Vulnérabilités / Smells (projet) | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Security hotspots | 0 | 0 | = |
| Coverage projet | 97,5 % | 97,5 % | = |
| Duplication | 0,4 % | 0,4 % | = |
| Ratings fiabilité / sécurité / maintenabilité | A / A / A | A / A / A | = |

## Lint log

`/lint-angular` — `Client/Angular/front`, branche `feature/nova-mss-weda-integration` (code seul), base `origin/next`, lint `tag:scope:mss`.

- **Baseline** : `nx affected -t lint` → **0 erreur** (avertissements seuls, préexistants : `max-lines`, jsdoc). Les 2 erreurs introduites par la passe qualité de /develop (jsdoc, prettier) avaient été corrigées avant.
- **Itérations** : aucune — rien à corriger. Pas de re-build : l'arbre n'a pas changé depuis la validation de /develop (build vert, `tag:scope:mss` 124 fichiers de test verts).
- **Erreurs restantes** : 0. Aucune règle corrigée à la main → rien à verser à `conventions/angular.md`.

## Lint mobile log

`/lint-mobile` — `Client/Mobile`, branche `feat/task-392-…` à `6636430`.

- **Baseline** : `npm run lint` → « All files pass linting » (0 erreur, 0 avertissement).
- **Itérations** : aucune. Aucun commit : rien à corriger. Build et tests déjà verts sur ce commit (passe qualité de /develop : 1346/1346).
- Aucune règle corrigée à la main → rien à verser à `conventions/angular.md`.

### Retour en /develop après le 1ᵉʳ passage de /e2e (deux rouges causés par le seed de la task)

- **Mobile, E2E-AI-001 rouge** : la ligne HPRIM épinglée (« Biologie à valider ») poussait `mail-non-lu` sous la barre d'onglets ; le long-press, joué en coordonnées, a ouvert l'onglet Patients (capture). Correction du helper `gestureBox` (`e2e/support/ui.ts`) : la cible est centrée, puis le point visé est vérifié par `elementFromPoint`, sinon erreur explicite. Commit `9b5ee19`. Convention `geste-recouvert` créée.
- **weda2, E2E-BIO-003 rouge** (« EN COURS » au lieu de « À TRAITER ») : E2E-BIO-001 cliquait `.first()` dans le filtre « à acquitter », qui ne range pas par date — il a acquitté le HPRIM au lieu du CDA. BIO-001 désigne maintenant le CDA par son uid relu du serveur (`mailBySubject`), à l'ouverture comme à la relecture. C'est le cas `.first()` après un filtre que la convention `seed-partage-des-deux-clients`, écrite pendant ce /develop, nommait déjà.
- Côté mobile, BIO-001 garde son `.first()` après la puce (liste rangée par date, vert) : à aligner dans une task de durcissement, noté en suite.

## E2E log

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

| Voie | Pourquoi | Résultat | Détail | Durée |
|---|---|---|---|---|
| mobile | api-mail + client-mobile touchés | ✅ verte (passage final, api-mail `667f81a4`, mobile `b792b15`) | 51 verts, 0 flaky, 0 rouge, 0 quarantaine | 8 min 15 s |
| angular | api-mail + client-angular touchés | ✅ verte (passage final, mêmes empreintes) | 60 verts, 0 flaky, 0 rouge ; 1 quarantaine (E2E-COMPOSE-002, posée par l'humain, task-350) | 8 min 08 s |
| gate | porte de parité | ✅ verte | 0 écart | 0,2 s |

Passage final rejoué après les correctifs de /review (tests api-mail et assertions e2e positives) : c'est exactement le code des PR. Le passage vert précédent (mobile 3ᵉ, angular 2ᵉ) l'était aussi.

**Passages précédents (rouges, causés par la task, corrigés en /develop)** :

| Passage | Voie | Rouge | Cause | Correction |
|---|---|---|---|---|
| 1 | mobile (11 min 40 s) | E2E-AI-001 ; flaky E2E-DELEG-004 | la ligne HPRIM épinglée pousse `mail-non-lu` sous la barre d'onglets ; le long-press ouvre l'onglet Patients | `gestureBox` centre la cible et vérifie le point touché (`9b5ee19`) |
| 1 | angular (8 min 36 s) | E2E-BIO-003 (« EN COURS ») ; flaky E2E-SETTINGS-003 | E2E-BIO-001 acquittait `.first()` du filtre, soit le HPRIM | BIO-001 désigne le CDA par son uid |
| 2 | mobile (8 min 10 s) | E2E-DELEG-002, E2E-DELEG-003 | la vérification du point, neuve, a vu le menu latéral encore en fermeture recouvrir la ligne | le geste attend que la cible soit découverte, 5 s max (`0c06958`) |

- **Flaky** : aucun au passage retenu (E2E-DELEG-004 mobile et E2E-SETTINGS-003 angular ont été verts au second essai lors du 1ᵉʳ passage).
- **Quarantaine** : E2E-COMPOSE-002 [angular], task-350 — non bloquante.
- **Divergence ouverte** : E2E-MAILBOX-002 [angular] (task-395) — la porte la signale **« à retirer »** : le test weda2 est revenu à la version du catalogue. Retrait = décision humaine.
- **Nouveau scénario** : E2E-BIO-003 v1 vert dans les deux clients.
- **Démontage** : aucun port tenu, aucun conteneur e2e résiduel.

### Retour en /develop après la 1ʳᵉ passe de /review (CHANGES REQUESTED)

- **❌ bloquant, corrigé** : la clause DoD « BAL déléguée — seules les valeurs signalées par le laboratoire portent `IsFlagged` » n'avait pas de test (une seule valeur, signalée « H »). `ADelegatedHprimWithResLines_…` porte maintenant une 2ᵉ ligne hors bornes **sans** indicateur, affirmée `IsFlagged == false`, et vérifie le texte délégué présent puis sans `RES|`, `TEX|`, `****LAB****`. Commit `667f81a4`.
- **⚠️ corrigé** : dans `AnHprimOutOfItsNorms…`, l'absence de la file « à acquitter » était lue après `IsFlagged` et n'était jamais tombée seule ; elle est lue en premier.
- **Preuve par mutation MN** (`… || result.PrimaryMaxValue.Length > 0`) : `AnHprimOutOfItsNorms…` rouge sur `Assert.DoesNotContain(uid, PendingAckUids)` (ligne 219) ; `ADelegatedHprimWithResLines_…` rouge sur `Assert.False(… IsFlagged)` de la valeur non signalée. Source restaurée par `cp` + `touch`, suites HPRIM + délégation 40/40 vertes.
- **⚠️ e2e, corrigés** : mobile E2E-BIO-003 relit `biology-ack-last` (preuve positive) avant l'absence d'« À TRAITER » (`b792b15`) ; weda2 E2E-BIO-003 affirme la classe `neutral` de la glycémie avant l'absence des couleurs d'anomalie.
- **Re-validation /review (avant correctifs)** : api-mail build + 5 suites vertes (integration 1026/1042, 16 skipped — hors fenêtre de minuit cette fois) ; mobile build vert ; weda2 build + `tag:scope:mss` 124 fichiers verts.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/319 — label `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/109 — label `awaiting-human-merge`
- `client-angular` (code seul, branche `feature/nova-mss-weda-integration`) : humain gère commit/push TFS et ouverture PR. Fichiers modifiés :

```
front/e2e/mss-e2e/specs/functional.e2e.ts
front/libs/mss/src/core/models/biology-value.model.ts
front/libs/mss/src/core/models/patient.model.ts
front/libs/mss/src/features/mail/components/mail-body/mail-body.component.ts
front/libs/mss/src/features/patient/components/biology-timeline/biology-timeline.component.html
front/libs/mss/src/features/patient/components/biology-timeline/biology-timeline.component.scss
front/libs/mss/src/features/patient/components/biology-timeline/biology-timeline.component.ts
front/libs/mss/src/ui/biology-value/biology-value.component.scss
front/libs/mss/src/ui/biology-value/biology-value.component.ts
front/libs/mss/src/ui/biology/biology.component.html
front/libs/mss/src/ui/biology/biology.component.scss
front/libs/mss/src/ui/biology/biology.component.ts
(nouveau) front/libs/mss/src/core/utils/biology-result.util.ts
(nouveau) front/libs/mss/src/features/mail/components/mail-body/mail-body.component.hprim.spec.ts
(nouveau) front/libs/mss/src/features/patient/components/biology-timeline/biology-timeline.component.partial.spec.ts
(nouveau) front/libs/mss/src/ui/biology/biology.component.hprim.spec.ts
```

## Code Review Summary


**Verdict : APPROVED** (2ᵉ passe). La 1ʳᵉ passe indépendante avait demandé un changement bloquant : la clause DoD « BAL déléguée — seules les valeurs signalées portent `IsFlagged` » n'avait pas de test. Le test a été ajouté et vu rouge sous mutation (`667f81a4`).

### Règle 1b — comportement → test d'intégration → preuve rouge

| Comportement (endpoint) | Test d'intégration | Preuve rouge |
|---|---|---|
| `IsFlagged` = indicateur du laboratoire seul (`GET biology/patients/{id}`) | nominal + `AnHprimOutOfItsNormsWithoutLaboratoryIndicator_…` | mutation MN (les bornes font l'anomalie) |
| « Anormaux non lus » ne compte que la valeur « H » ; vide sans indicateur (`GET biology/abnormal-unread`) | nominal (`AbnormalCount == 1`) + négatif | MN |
| Pas dans la file « à acquitter » sans indicateur (`GET biology-acks/pending-mail-uids`) | `AnHprimOutOfItsNorms…` (lue en premier) + témoin `AnHprimFlaggedByTheLaboratory_IsToAcknowledge` | MN, rouge sur l'assertion de la file elle-même |
| Texte sans `****LAB****` / `TEX|` / `RES|` (`GET …/emails/content/{uid}`) | `TheHprimText_IsServedWithoutItsTechnicalLines` | mutation MT (texte non nettoyé) |
| BAL déléguée : texte nettoyé, seules les valeurs signalées portent `IsFlagged`, rien en base ni dans Redis, « anormaux non lus » vide | `ADelegatedHprimWithResLines_…` | MT + MN |

### Constats

- ✅ api-mail : `IsFlagged = BiologyInterpretation.IsFlaggedCode(...)`, la même règle que `CdaParsingService`. Pas de piège CRLF : `HprimReader` rogne les lignes et recompose le texte avec `\n`. Aucun journal ajouté, donc aucune donnée de santé exposée. Règle 14 : la voie déléguée reste en mémoire.
- ✅ Les clients mettent en évidence par le seul indicateur. « Partiel » s'affiche pour un statut P, « code labo » pour `LABORATORY-LOCAL`, la seconde valeur est affichée.
- ✅ Les gestes e2e mobiles (`gestureBox`) centrent leur cible et vérifient le point touché. Un recouvrement passager est attendu 5 s au plus.
- ⚠️ **Données déjà en base (à arbitrer)** : les HPRIM analysés depuis le merge de task-390 (26/10) gardent `IsFlagged = true` sur leurs valeurs hors bornes sans indicateur, et un `Body` qui contient les lignes techniques. Il n'y a pas de remise à niveau automatique. Il faut une ré-analyse ou une requête SQL, sans objet si `develop` n'est déployé nulle part.
- ⚠️ BIO-001 mobile clique encore `.first()` après la puce. Il est vert parce que la liste est triée par date, mais c'est fragile. À aligner dans une task de durcissement.
- ⚠️ Le repli `top.contains(el)` de `gestureBox` peut accepter un élément qui recouvre la cible depuis le shadow root d'un de ses ancêtres. Le risque est faible.
