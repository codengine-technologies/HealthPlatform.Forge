# todo-task-372.md — L'import dans le dossier Weda classe chaque document chez le bon patient, et dit vrai sur ce qui a été importé ou envoyé

**Repos**: client-angular, api-mail
**Dependencies**: task-371 (le mail affiché est celui qui est sélectionné — sans elle, l'import reçoit le contenu du mail précédent) — **mergée et archivée** (vérifié le 2026-10-18)
**Epic**: E019
**Single frontend**: true — l'import Weda n'existe que dans weda2 embarqué.
**Priorité**: **1** — erreurs d'identito-vigilance : un document médical classé dans le dossier d'un autre patient, avec une présélection présentée comme fiable (trouvée par INS).

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-09, ANG-18 ✔ (volet import), ANG-47, ANG-48, ANG-49, ANG-63, ANG-64**).
> Décisions de l'intégration : mémoire `weda-nova-integration` (EPIC E019).

## Ce qui est établi

> **Revérifié dans le code le 2026-10-18** (avant `/start`) : les sept constats sont **toujours présents**. Le
> composant `weda-import` n'a pas changé depuis `58bfffe9` (2026-10-10, avant l'audit) ; `occurrence` n'apparaît
> nulle part dans `libs/mss/src`. Les numéros de ligne ci-dessous sont ceux de l'audit et peuvent avoir glissé.
> - **Constat ajouté** : la fenêtre d'import (`dialogOpen`) ne se ferme pas quand le mail sélectionné change
>   (clavier, temps réel). « Importer » utiliserait alors le mail B avec les documents de A. Traité au point 1.
> - **api-mail** : `GET …/download/attachment/{name}?occurrence=` est géré depuis AUD-41 et prouvé par
>   `MailAttachmentDownloadIntegrationTests.DownloadAttachment_WithOccurrenceOne_ReturnsTheSecondHomonym`. Seul
>   weda2 reste à faire : suivre le rang de chaque pièce et le transmettre.

- **ANG-09** — `weda-import.component.ts:189-194, 258-287, 530-552` : rien ne lie une préparation d'import à l'ouverture qui l'a lancée. « Annuler » pendant la préparation puis ouverture sur B : la résolution tardive de A sélectionne le patient de A ; aucun bouton radio n'est coché, l'invite est masquée, « Importer » est actif.
- **ANG-48** — `weda-import.component.ts:540-551`, `weda-import.utils.ts:175-180` : un message portant les documents de deux patients présélectionne le premier trouvé par INS et coche tous les documents.
- **ANG-47** — `weda-import.component.ts:442-519` : le compte rendu d'un import (succès ou erreur) reste affiché sur le message suivant.
- **ANG-18 (import)** — `weda-import.component.ts:601-613` : deux pièces de même nom → la première est importée deux fois, la seconde jamais, « 2 document(s) importé(s) » affiché (`occurrence` jamais transmis, `mss-api.service.ts:1884-1895`).
- **ANG-49** — `mail-compose.component.ts:902-904, 1354-1364, 1714-1726, 1775-1788` : l'avis `document-sent` envoie tous les `fileStreamId` de l'intention, même ceux retirés ou écartés ; un envoi mis de côté (202) ou en file n'en envoie aucun. Weda écrit donc de fausses traces « Traces MSSanté », et en omet de vraies.
- **ANG-63** — « Envoyer » depuis le dossier Weda n'aboutit à rien, sans message, quand l'intégration est indisponible.
- **ANG-64** — import en échec ou hors délai : « Réessayez » crée des doublons (import Weda non transactionnel).

## Objective

Que l'import dans le dossier patient Weda **ne classe jamais un document chez le mauvais patient**, que la présélection d'un dossier ne soit faite que si elle est certaine, et que ce que weda2 dit à Weda et au médecin (documents importés, documents envoyés) corresponde exactement à ce qui s'est passé.

### Périmètre

1. **Préparation liée à son ouverture** : compteur de génération vérifié après chaque attente ; sélection remise à zéro si le patient choisi n'est plus listé ; « Annuler » indisponible pendant un import en cours ; **fenêtre fermée (et préparation abandonnée) quand le mail sélectionné change**.
2. **Présélection sûre** : un dossier n'est présélectionné que si **tous** les documents cochés se résolvent vers le même dossier ; sinon, choix explicite et seuls les documents du patient choisi cochés par défaut.
3. **Compte rendu rattaché au message** : succès et erreur effacés au changement de mail.
4. **Pièces homonymes** : le rang `occurrence` est transmis au téléchargement (le serveur le gère depuis AUD-41).
5. **Avis d'envoi exact** : `fileStreamIds` calculés sur les pièces réellement jointes au moment de l'envoi ; pas d'avis si aucune pièce de l'intention ne part.

> **⚠️ Arbitrage humain requis — envois différés.** Pour un envoi mis de côté (202, « à confirmer avec la
> carte ») ou mis en file hors ligne, la trace Weda doit-elle (a) être écrite plus tard, à l'envoi
> effectif (api-mail ou weda2 doit alors la déclencher), ou (b) ne pas l'être, en documentant la
> limite ? La forge ne tranche pas.
>
> **Décision humaine (2026-10-13) : (b) pas de trace pour un envoi différé, limite documentée.** weda2
> n'écrit la trace que pour un envoi immédiat réussi ; la limite est documentée dans E019 (et dans la
> `## Develop log`). Écrire la trace à l'envoi effectif reste un chantier à part (api-mail devrait prévenir
> Weda).

6. **Intégration indisponible** : quand weda2 est embarqué mais que l'intégration ne répond pas, un message clair indique de passer par l'ancien écran.
7. **Échec ou délai dépassé** : message « vérifiez le dossier patient avant de réessayer ». Côté Weda (hors forge) : transaction couvrant tout l'import, à signaler à l'équipe Weda.

## Definition of Done

- [x] Build et tests weda2 verts ; api-mail vert
- [x] Tests unitaires et de composant rouges d'abord :
  - [x] préparation de A abandonnée puis ouverture sur B : la résolution de A ne modifie ni la liste ni la sélection de B
  - [x] fenêtre d'import ouverte sur A, sélection de B : la fenêtre se ferme, aucun import de B avec les documents de A
  - [x] deux documents de deux patients différents : aucune présélection, choix exigé
  - [x] le compte rendu d'import de A n'est plus affiché sur B
  - [x] deux pièces `scan.pdf` : deux téléchargements avec `occurrence` 0 et 1, deux contenus distincts envoyés à Weda
  - [x] pièce de l'intention retirée avant l'envoi : son `fileStreamId` n'est pas dans l'avis ; aucune pièce de l'intention : pas d'avis
  - [x] intégration indisponible : le message s'affiche
- [x] Test d'intégration de bout en bout pour `GET …/download/attachment/{name}?occurrence=1` : **existe déjà depuis AUD-41** (`MailAttachmentDownloadIntegrationTests.DownloadAttachment_WithOccurrenceOne_ReturnsTheSecondHomonym`, task-342) — vérifié le 2026-10-18
- [x] Scénario E2E-WEDA-002 versionné (v2) : import d'un message à deux documents de deux patients, sans présélection ; pièces homonymes importées toutes deux — angular `requis`, mobile `non-applicable` (l'import Weda n'existe pas sur mobile)
- [x] Scénario E2E-WEDA-003 versionné (v2) : pièce de l'intention retirée → aucune trace d'envoi pour elle
- [x] Trou du filet : ligne dans `conventions/e2e.md`
- [x] INS ni affichée ni journalisée (inchangé)

## Manual Test Plan

1. Weda Échanges, mail portant les CDA de deux patients connus par INS : « Importer » → aucun dossier présélectionné ; choisir un patient → seuls ses documents sont cochés.
2. Ouvrir l'import de A, cliquer « Annuler » pendant « Préparation… », ouvrir l'import de B → la fenêtre de B n'a aucune sélection héritée de A.
3. Importer A, sélectionner B → aucun « document(s) importé(s) » affiché sous B.
4. Mail avec deux pièces `scan.pdf` différentes → les deux sont classées, chacune avec son contenu.
5. Depuis le dossier Weda, « Envoyer » un document, le retirer de la rédaction, joindre autre chose, envoyer → aucune trace « document envoyé » pour le document retiré.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — intégration DPI ↔ MSSanté (import des documents reçus dans le dossier)
- **Exigences DSR honorées** : identito-vigilance du rattachement d'un document reçu au dossier patient (RNIV : pas de rapprochement présenté comme certain sans concordance des traits)
- **INS** : récupérée depuis les documents (CDA) et utilisée pour la résolution côté Weda ; la présélection n'a lieu que si toutes les identités concordent ; INS jamais affichée ni journalisée par weda2
- **Authentification PS** : inchangée (session PSC / e-CPS du praticien)
- **Habilitations** : inchangées (droits Weda du praticien sur le dossier)
- **Interop CI-SIS** : CDA r2 et IHE XDM — lecture seule des documents reçus
- **Tracé PGSSI-S** : traces « Traces MSSanté » de Weda exactes (documents réellement envoyés) ; décision sur les envois différés (arbitrage ci-dessus)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : fix/task-372-import-weda-bon-patient — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-372-import-weda-bon-patient (catalogue e2e `Api/Mail/e2e/scenarios.yml` : E2E-WEDA-002 et 003 en v2)
- `client-angular` (code-only) : la forge écrit le code sur la branche checked out dans `Client/Angular/` (au /start : `feature/nova-rewriting-mss-weda-integration`, propre, HEAD `0bc7833a`) — l'humain gère branche, commit, push, PR TFS

## Develop log

**api-mail** (`fix/task-372-import-weda-bon-patient`, `7729bfad`) — aucun code de production : outil e2e et catalogue.
- `mss.mail.e2e message --create <objet> --kind weda-import` (`E2eWedaImportMessage`) : deux `IHE_XDM.ZIP` (lettre de liaison du fixture, INS de test `1.2.250.1.213.1.4.10` et traits propres à chaque patient, identifiant de document propre) et deux `scan.pdf` de tailles différentes.
- `E2eWedaImportMessageTests` (2) : les deux enveloppes sont lues par `CdaParsingService` avec l'INS et les traits de leur patient ; les deux pièces homonymes ont deux tailles.
- Catalogue : E2E-WEDA-002 v2, E2E-WEDA-003 v2.
- Règle 1b : aucun comportement d'endpoint ajouté ni modifié. `?occurrence=` est servi depuis AUD-41 et prouvé par `MailAttachmentDownloadIntegrationTests.DownloadAttachment_WithOccurrenceOne_ReturnsTheSecondHomonym` (task-342).
- Validation : build Release de la solution vert, `mss.mail.api.tests` 1 239/1 239. Build en `-c Release` : l'AppHost Aspire de l'humain (`dotnet run --launch-profile https`, 17 h 14) verrouille `src/Api/bin/Debug`.

**client-angular** (code-only, branche `feature/nova-rewriting-mss-weda-integration`) — tests écrits d'abord, vus rouges (11 de composant, 6 unitaires d'import, 2 d'API, 3 de rédaction, 4 d'intégration), puis verts.
- ANG-09 / fenêtre : compteur de génération (ouverture, « Annuler », changement de message) vérifié après chaque attente (préparation, recherche, import) ; un effet sur le message affiché (dossier + uid) referme la fenêtre et efface le compte rendu ; « Annuler » désactivé pendant l'import ; « Importer » exige que le dossier choisi soit encore proposé, et une nouvelle recherche oublie un dossier qu'elle ne propose plus.
- ANG-48 : présélection seulement si chaque identité des documents est trouvée par INS, toutes vers le même dossier. Documents de plusieurs patients : rien n'est coché d'office ; choisir un patient coche le PDF des CDA de ce patient (par INS) et décoche les autres. Clé d'identité extraite (`documentIdentityKey`, `weda-patient-panel.utils.ts`).
- ANG-47 : succès et erreur effacés au changement de message ; un import en cours quand le message change ne lui attribue pas son compte rendu.
- ANG-18 (import) : chaque pièce porte son rang parmi ses homonymes, dans l'ordre de `mail.attachments` (même règle que le mobile, task-329) ; le PDF d'un CDA prend le rang de la pièce médicale de même nom. `MssApiService.downloadAttachment(…, occurrence = 0)` ajoute `?occurrence=n` à partir de 1 (adresse historique pour la première).
- ANG-49 : chaque pièce de la rédaction venue de l'intention porte son `fileStreamId` ; l'avis cite ceux encore joints au moment de l'envoi (ni retirés, ni refusés pour leur taille), et n'est pas envoyé si aucun ne part. Envoi différé (202, file) : pas d'avis, décision humaine (b), limite à documenter dans E019.
- ANG-63 : `EmbeddedHostService.composeRequested` lit `compose=1` dans l'adresse d'entrée de l'iframe ; sans intégration disponible, le fournisseur d'intention lève `integration-unavailable` et la messagerie affiche « … Envoyez-le depuis l'ancien écran de messagerie. ». **Côté Weda (hors forge, à faire par l'humain / l'équipe Weda)** : `nova-mss-host.js` doit ajouter `compose=1` à l'URL de l'iframe quand la page est en `Mode=1` (fonction `isComposeRequest()`). Sans ce changement, le comportement reste celui d'avant (aucun message).
- ANG-64 : délai dépassé et échec générique disent « Vérifiez le dossier patient avant de réessayer : une partie des documents a pu être importée. » ; une lecture des documents en échec dit qu'elle n'a rien envoyé. **Côté Weda (hors forge)** : une transaction couvrant tout l'import reste à signaler à l'équipe Weda.
- e2e : E2E-WEDA-002 v2 (étape 4 : message déposé par l'outil, faux hôte qui trouve chaque patient par INS, aucun dossier présélectionné, rien de coché, deux tailles reçues), E2E-WEDA-003 v2 (étape 5 : document retiré, pièce à la main, aucun avis). Faux hôte : `FAKE_HOST_PATIENTS_BY_INS`.
- Validation : `nx test mss weda2` 2 729 passés (14 ignorés, préexistants), `nx build weda2` vert, specs e2e compilées (`tsc -p e2e/mss-e2e`).
- Passe qualité §Q : relecture du diff, aucun nettoyage retenu (pas de commit `refactor`). Aucune opération git sur client-angular.

## Sonar log

- Mode A (chaîné), SonarQube 9.9.8, branche `fix/task-372-import-weda-bon-patient` (HEAD `7729bfad`). 1 itération, aucun correctif.
- Référence avant analyse : bugs 0, vulnérabilités 0, code smells 0, couverture 97,9 %, notes A/A/A, Quality Gate OK.
- Analyse de la branche (build Release, 5 passes OpenCover : 195 + 3 661 + 690 + 1 239 + 896 verts, 16 ignorés préexistants) : Quality Gate **OK**. Nouveau code : 0 issue, 0 hotspot, couverture 96,8 %, duplication 0,11 %. Le diff ne touche que l'outil e2e et ses tests (hors couverture).
- Phase 2 sans objet (cibles projet atteintes). Aucune consigne nouvelle pour `conventions/csharp.md`.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | = |
| New coverage | — | 96,8 % | cible 95 % |
| Bugs / Vulnérabilités / Code smells | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Coverage projet | 97,9 % | 97,9 % | = |
| Duplication | 0,4 % | 0,4 % | = |
| Ratings (fiabilité / sécurité / maintenabilité) | A / A / A | A / A / A | = |

- Next step : `/lint-angular task-372`.

## Lint log

- Mode A, code-only (`Client/Angular/front`, branche `feature/nova-rewriting-mss-weda-integration`, rien de commité). Contournement de task-367 : `npx eslint --format json` sur les 20 fichiers `.ts` de la task, avertissements attribués par `git diff -U0 HEAD` (les specs `.spec.ts` sont ignorées par la configuration).
- Référence : 4 erreurs, toutes de la task (3 `prettier/prettier`, 1 `jsdoc/require-jsdoc` sur le constructeur de `WedaImportComponent`), 44 avertissements dont 1 de la task (`@example` vide de `createWedaImportMessageElsewhere`).
- Itération 1 : JSDoc et `@example` écrits à la main, `eslint --fix` sur 3 fichiers (fins de ligne CRLF conservées).
- Après : **0 erreur**, avertissements restants tous antérieurs à la task. `nx test mss weda2` ✓ (2 729), `nx build weda2` ✓, `tsc -p e2e/mss-e2e` ✓.
- Next step : `/lint-mobile task-372` (client-mobile non touché → skip).

## Lint mobile log

- Skipped : `client-mobile` n'est pas dans les `**Repos**` de la task, aucune branche ni aucun changement (l'import Weda n'existe que dans weda2 embarqué).
- Next step : `/e2e task-372`.

## E2E log

| Voie | Commande | Résultat |
|---|---|---|
| mobile | `npm run e2e:headless` (Client/Mobile) | ✅ 37 verts, 0 flaky, 0 rouge, parité verte |
| angular | `npm run e2e:mss` (Client/Angular/front) | ✅ 45 verts, 0 flaky, 0 rouge, parité verte |
| porte | `mss.mail.e2e gate --report mobile=… --report angular=…` | ✅ code 0 |

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

- Voies jouées : api-mail touché (outil e2e, catalogue) → mobile ; client-angular touché → Angular.
- Flaky : aucun.
- Quarantaine (humaine, non bloquante) : [angular] E2E-COMPOSE-002 — correction task-350 (Passed à ce run).
- Divergences ouvertes : aucune.
- Parité : E2E-WEDA-002 v2 et E2E-WEDA-003 v2 ✅ angular, — mobile (non-applicable). Matrice complète dans le rapport de la porte (`forge-e2e-372/gate.md`, 47 scénarios, aucun écart).
- **Preuve rouge par mutation** (banc `--serve-only`, `--retries=0`, une mutation à la fois, restauration vérifiée) :
  - M1 ANG-48, présélection réinjectée (`byIns.length > 0`) → E2E-WEDA-002 rouge : « aucun dossier présélectionné : les documents désignent deux patients » (Received: checked).
  - M2 ANG-18, `occurrence` non transmis → E2E-WEDA-002 rouge : « chaque pièce homonyme arrive avec son propre contenu » (Expected 2, Received 1).
  - M3 ANG-49, avis calculé sur toute l'intention → E2E-WEDA-003 rouge : « aucun avis pour le document retiré ». Premier essai de M3 sans bundle (méthode laissée sans appel, TS6133 : piège `mutation-non-servie`, occurrence 6) ; deuxième essai tombé sur un `click` pendant le rechargement du bundle (non retenu) ; troisième essai rouge sur l'assertion attendue.
  - Après restauration : E2E-WEDA-002 et 003 verts.
- ANG-09, ANG-47, ANG-63 et ANG-64 sont prouvés par les tests de composant et unitaires (cas de course et d'indisponibilité non reproductibles au banc sans modifier le faux hôte).
- Démontage : aucun conteneur e2e résiduel, aucun processus `mss.mail` restant.
- Écrans modifiés sans spec e2e modifié : aucun (import Weda et rédaction couverts par E2E-WEDA-002/003).
- Banc joué après l'arrêt, par l'humain, de son AppHost de dev (verrou sur `src/Api/bin/Debug`).

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/301 — label `awaiting-human-merge` (outil e2e, tests du message, catalogue E2E-WEDA-002/003 v2 ; aucun code de production).
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR. Branche `feature/nova-rewriting-mss-weda-integration`. Liste des fichiers modifiés :
  - `front/apps/weda2/src/lib/embedded/compose-intent.provider.spec.ts`
  - `front/apps/weda2/src/lib/embedded/compose-intent.provider.ts`
  - `front/apps/weda2/src/lib/embedded/embedded-host.model.ts`
  - `front/apps/weda2/src/lib/embedded/embedded-host.service.spec.ts`
  - `front/apps/weda2/src/lib/embedded/embedded-host.service.ts`
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/e2e/mss-e2e/support/e2e-backend.ts`
  - `front/e2e/mss-e2e/support/weda-host.ts`
  - `front/libs/mss/src/core/services/mss-api.service.spec.ts`
  - `front/libs/mss/src/core/services/mss-api.service.ts`
  - `front/libs/mss/src/core/utils/compose-intent.utils.spec.ts`
  - `front/libs/mss/src/core/utils/compose-intent.utils.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose-intent.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.ts`
  - `front/libs/mss/src/features/mail/components/weda-import/weda-import.component.html`
  - `front/libs/mss/src/features/mail/components/weda-import/weda-import.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/weda-import/weda-import.component.ts`
  - `front/libs/mss/src/features/mail/components/weda-import/weda-import.utils.spec.ts`
  - `front/libs/mss/src/features/mail/components/weda-import/weda-import.utils.ts`
  - `front/libs/mss/src/features/mail/components/weda-patient-panel/weda-patient-panel.utils.spec.ts`
  - `front/libs/mss/src/features/mail/components/weda-patient-panel/weda-patient-panel.utils.ts`
- **Côté Weda (hors forge, à faire par l'humain / l'équipe Weda)** :
  - `FolderMedical/WedaEchanges/NovaMss/nova-mss-host.js` : ajouter `compose=1` à l'URL de l'iframe quand la page est en `Mode=1` (`isComposeRequest()`), au **premier chargement seulement** (un rechargement de l'iframe ne doit pas redemander la rédaction). Sans ce changement, ANG-63 reste sans message.
  - Import Weda : une transaction couvrant tout `file-documents` (ANG-64), à signaler à l'équipe Weda.

## Code Review Summary

**APPROVED** — 0 bloquant, 4 suggestions.

- Validation : api-mail build ✓, tests 195 + 3 661 + 690 + 1 239 + 896 verts (16 ignorés préexistants) ; client-angular `nx build weda2` ✓, `nx test mss weda2` 2 729 verts (14 ignorés préexistants).
- Règle 1b : aucun comportement d'endpoint ajouté ni modifié dans api-mail. Comportement consommé : `GET …/download/attachment/{name}?occurrence=1` → `MailAttachmentDownloadIntegrationTests.DownloadAttachment_WithOccurrenceOne_ReturnsTheSecondHomonym` (task-342, AUD-41).
- Double verrou e2e : `## E2E log` vert ; E2E-WEDA-002/003 v2 au catalogue et dans `functional.e2e.ts`, prouvés rouges par mutation (M1, M2, M3).
- weda2 :
  - `weda-import.component.ts` — ✅ génération vérifiée après chaque attente ; fenêtre et compte rendu rattachés au message ; présélection seulement si toutes les identités désignent par INS le même dossier.
  - `weda-import.utils.ts`, `weda-patient-panel.utils.ts` — ✅ rang des homonymes (même règle que le mobile), clé d'identité extraite et partagée.
  - `mss-api.service.ts` — ✅ `occurrence` facultatif, adresse historique pour la première pièce.
  - `mail-compose.component.ts` — ✅ `fileStreamId` porté par la pièce ; avis calculé à l'envoi, absent si aucun document ne part.
  - `embedded-host.service.ts`, `compose-intent.provider.ts`, `compose-intent.utils.ts` — ✅ `integration-unavailable` levé seulement si Weda a demandé la rédaction.
- Suggestions (non bloquantes) :
  1. `compose=1` doit n'être posé par Weda qu'au premier chargement de l'iframe, sinon un rechargement réafficherait le message d'indisponibilité (consigné dans `## PRs`).
  2. Un import abandonné par un changement de message continue chez Weda, mais son compte rendu est perdu ; acceptable (le praticien a quitté le message), à garder en tête.
  3. Documents de plusieurs patients : le PDF d'un CDA rapproché seulement par traits reste décoché après le choix (prudence voulue, RNIV).
  4. Les autres appels à `downloadAttachment` (lecture, transfert) ignorent encore les homonymes : périmètre de task-376 (ANG-18, lecture et transfert), qui pourra réutiliser `occurrence`.

## Timings

*(généré par `tools/timing/report.sh --task task-372 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 8.6 s | — | — | — | — |
| /develop | ok | 22 min 24 s | 2 (27 s) | 4 (1 min 14 s) | — | api-mail 1B/3T, client-angular 1B/1T |
| /sonar | ok | 6 min 54 s | 1 (21 s) | 5 (5 min 00 s) | 2 (46 s) | 1 itération(s), api-mail 1B/5T |
| /lint-angular | ok | 1 min 49 s | 1 (20 s) | 1 (22 s) | — | 1 itération(s), client-angular 1B/1T |
| /lint-mobile | skipped | 0.4 s | — | — | — | client-mobile non touché |
| /e2e | ok | 1 h 28 min | — | — | — | e2e ×3 (13 min 26 s) |
| /review | ok | 5 min 13 s | 3 (11 s) | 3 (3 min 46 s) | — | api-mail 2B/2T, client-angular 1B/1T |
| **Total cycle** | | **2 h 05 min** | **7 (1 min 20 s)** | **13 (10 min 23 s)** | **2 (46 s)** | |

Autres commandes mesurées : lint ×1 (5.5 s)
