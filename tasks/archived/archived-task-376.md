# todo-task-376.md — Rédiger dans weda2 : jamais de contenu perdu, jamais de double envoi, jamais d'envoi incomplet présenté comme réussi

**Repos**: client-angular, client-mobile, api-mail
**Dependencies**: — (aucune)
**Epic**: E009
**Single frontend**: false — weda2 et le mobile (décision humaine du 2026-10-13).
**Priorité**: **1** — un courrier médical peut partir deux fois, partir sans ses pièces jointes avec « envoyé avec succès », annuler à tort un envoi antérieur, ou être perdu sans avertissement à la fermeture de la rédaction.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-14 ✔, ANG-15 ✔, ANG-16 ✔, ANG-17, ANG-18 ✔ (lecture et transfert), ANG-19, ANG-26, ANG-42, ANG-43, ANG-44, ANG-45, ANG-46, ANG-75**).

## Ce qui est établi

- **ANG-14** — la remise incertaine du serveur (503 `MAIL_DELIVERY_UNCERTAIN`, 502 de la route brouillon, décision task-330) n'est reconnue nulle part : la rédaction affiche « Erreur lors de l'envoi » et réactive Envoyer ; les envois en attente affichent « le message reste prêt à partir » ; le modèle n'a pas `deliveryUncertain`.
- **ANG-15** — `mail-compose.component.ts:707` : seul `doClose` vide le contexte « annule et remplace ». « Annuler et remplacer » sur X puis « Nouveau message » : le nouveau message part par `cancel-and-replace` et X est marqué « [ANNULÉ] ».
- **ANG-16** — `mail-compose.component.ts:509-541, 2125-2195` : l'identifiant de brouillon est posé avant toute création côté serveur ; `saveAndClose` fait un PUT (404 sur un id inconnu) et ferme : **tout le contenu est perdu**. Un premier autosave en échec rend l'envoi impossible.
- **ANG-17** — « Nouveau message », clic sur un brouillon de la liste, intention de l'hôte, rechargement : la rédaction est remplacée sans être enregistrée ; aucun `beforeunload`.
- **ANG-18** — `occurrence` jamais transmis : au transfert, deux pièces homonymes deviennent deux copies de la première ; à la lecture, la seconde n'est pas consultable.
- **ANG-19** — Envoyer est actif avant la fin du téléchargement des pièces d'un transfert : le message part sans elles.
- **ANG-26** — `failedActionsCount` ignoré ; une confirmation d'envoi est annulée en quittant la page.
- **ANG-42 à ANG-46, ANG-75** — un modèle écrase citation et signature ; signature en double ou sous la citation ; adresse saisie sans Entrée ignorée, Cc/Cci masqués mais destinataires ; refus explicites du serveur (taille, opposition, verrou) jamais affichés ; brouillon « annule et remplace » envoyé sans carte comme un message ordinaire ; autosave non relancé après échec, contact sans adresse principale, doublons de modèles, aperçu de correction d'un autre message, dialogue de doublons qui garde son acquittement.

## Objective

Que ce que le médecin écrit **ne soit jamais perdu**, qu'un message **ne parte jamais deux fois ni incomplet** sans qu'il le sache, que « annule et remplace » ne vise **que** le message choisi, et que chaque refus ou incertitude du serveur lui soit dit en clair.

### Périmètre

1. **Remise incertaine** reconnue (code et 502 brouillon), `detail` du serveur affiché, nouvelle tentative bloquée ; statut 0 et 504 traités comme incertains ; `deliveryUncertain` et `failedActionsCount` dans les modèles et l'écran des envois en attente.
2. **Annule et remplace** : contexte vidé à chaque ouverture qui n'est pas un remplacement ; `sendMailDirect` route aussi sur le contexte restauré d'un brouillon ; `warning` de la réponse affiché.
3. **Brouillon** : identifiant adopté seulement après une création réussie ; en cas d'échec, la rédaction reste ouverte et le médecin est prévenu ; sur 404 à l'envoi, envoi direct.
4. **Remplacement de la rédaction** : un seul chemin « enregistrer puis ouvrir » pour tous les déclencheurs ; `beforeunload` tant qu'il reste du contenu non enregistré.
5. **Pièces jointes** : transfert par référence (`sourceFolderPath/sourceUid/sourceOccurrence`, résolu par `OutgoingMailService`) plutôt que retéléchargement ; à défaut, `occurrence` transmis et Envoyer désactivé tant que des pièces sont en cours ; erreur de pièce visible jusqu'à une action explicite.
6. **Refus explicites** : `detail` affiché pour les 400 et 409 ; taille totale calculée avec les lectures en cours.
7. Corrections de **ANG-42 à ANG-44, ANG-46, ANG-75**.

> **⚠️ Arbitrage humain requis — le client mobile.** Le mobile rédige et envoie aussi (réponse, transfert,
> brouillons, envois en attente). Il n'a pas été audité. Inclure `client-mobile` (audit ciblé de la
> rédaction mobile dans le `/develop`), ou ouvrir une task mobile dédiée ?
>
> **Décision humaine (2026-10-13, avant `/forge 368 to 381`) : inclure le mobile.** `/develop` audite le
> même périmètre sur `client-mobile` et y corrige les défauts trouvés ; les scénarios e2e de la task sont
> `requis` sur angular **et** mobile.

## Definition of Done

- [ ] Build et tests verts : weda2, api-mail
- [ ] Tests unitaires et de composant rouges d'abord, client-angular :
  - [ ] 503 `MAIL_DELIVERY_UNCERTAIN` : message « peut-être parti », Envoyer bloqué ; même chose pour le 502 de la route brouillon, le statut 0 et le 504
  - [ ] « Annuler et remplacer » puis « Nouveau message » : l'envoi passe par `sendmail`, pas par `cancel-and-replace`
  - [ ] premier autosave en échec puis fermeture : la rédaction reste ouverte avec un message ; aucune requête PUT sur un identifiant jamais créé
  - [ ] clic sur un brouillon de la liste pendant une rédaction : la rédaction en cours est enregistrée avant d'être remplacée
  - [ ] transfert d'un mail à deux pièces homonymes : deux pièces distinctes envoyées ; Envoyer désactivé pendant leur récupération
  - [ ] adresse tapée sans Entrée puis Envoyer : elle est ajoutée (ou l'envoi est refusé avec un message) ; Cc/Cci non vides non masquables
  - [ ] un 409 d'opposition patient affiche le `detail` du serveur
  - [ ] appliquer un modèle en réponse conserve citation et signature
- [ ] Test d'intégration de bout en bout pour l'envoi d'un transfert par référence (`POST …/sendmail` avec pièces `sourceFolderPath/sourceUid/sourceOccurrence`) : les deux pièces homonymes d'origine sont dans le message remis (lu côté serveur de messagerie du test), vu rouge si l'occurrence est ignorée (règle 1b) — s'il n'existe pas déjà
- [ ] Scénarios E2E :
  - [ ] E2E-COMPOSE-005 (renuméroté au sync develop : task-379 a pris le 004) « Une remise incertaine n'est jamais présentée comme un échec à renvoyer » ajouté (angular `requis`, mobile selon l'arbitrage)
  - [ ] E2E-DETAIL-001 versionné : le transfert d'un mail à deux pièces homonymes les envoie toutes deux
  - [ ] E2E-DRAFT-003 « Fermer une rédaction récente ne perd rien » ajouté
- [ ] Trou du filet : lignes dans `conventions/e2e.md`
- [ ] Aucune donnée de santé (corps, pièces) ajoutée aux journaux

## Manual Test Plan

1. Couper la connexion SMTP du serveur de test après DATA (banc) : l'écran dit « Ce message est peut-être parti… », Envoyer est bloqué.
2. « Annuler et remplacer » sur un envoi X, puis « Nouveau message » à un autre confrère, envoyer → X n'est pas marqué annulé.
3. Rédiger 10 s, cliquer sur un autre mail → le brouillon est enregistré ; rouvrir les brouillons : le texte est là.
4. Transférer un mail portant deux `document.pdf` différents → le confrère reçoit les deux documents.
5. Transférer un mail portant un IHE_XDM, cliquer aussitôt sur Envoyer → impossible tant que la pièce n'est pas jointe.
6. Patient opposé non acquitté : l'envoi affiche le motif du serveur.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif de l'envoi MSSanté
- **Exigences DSR honorées** : non applicable — rétablit la fiabilité de l'envoi (pas de doublon, pas d'envoi incomplet silencieux)
- **INS** : non applicable en écriture ; les documents transférés gardent leur identité (XDM inchangé)
- **Authentification PS** : PSC / e-CPS ; aucun envoi sans carte (règle inchangée : mise de côté puis confirmation)
- **Habilitations** : inchangées
- **Interop CI-SIS** : IHE XDM — les pièces d'origine sont transférées à l'identique, par référence
- **Tracé PGSSI-S** : envois, annulations (annule et remplace) et remises incertaines tracés comme aujourd'hui, désormais sur le bon message
- **Consentement patient** : opposition à l'envoi vers Mon Espace Santé — le refus du serveur est affiché
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : fix/task-376-redaction-sans-perte-ni-double-envoi — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-376-redaction-sans-perte-ni-double-envoi
- `client-mobile` (pushed) : fix/task-376-redaction-sans-perte-ni-double-envoi — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-376-redaction-sans-perte-ni-double-envoi
- `client-angular` (code-only) : la forge écrit le code sur la branche checked out dans `Client/Angular/` (snapshot au `/start` : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS

> **Vérification d'actualité (2026-10-22, avant `/start`).** Les ✔ de l'audit signifient « contre-vérifié », pas « corrigé ». Tous les constats sont toujours présents dans weda2 (ANG-14, 15, 16, 17, 18 lecture/transfert, 19, 26). Déjà livré ailleurs : la résolution par référence côté serveur (`OutgoingMailService.ResolvePartsByReferenceAsync`, `AttachmentDto.SourceOccurrence`) — couverte seulement par un test unitaire, le test d'intégration de la DOD reste à écrire ; `MssApiService.downloadAttachment(…, occurrence)` (task-372) réutilisable pour la lecture. Mobile : `sourceUid/sourceOccurrence` présents, aucune gestion de la remise incertaine.

## Timings

*(généré par `tools/timing/report.sh --task task-376 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 56 s | — | — | — | — |
| /develop | ok | 4 min 55 s | 18 (13 min 47 s) | 21 (39 min 23 s) | — | api-mail 7B/8T, client-mobile 4B/6T, client-angular 7B/7T, reprise B5 |
| /sonar | skipped | 1.9 s | 3 (3 min 44 s) | 10 (16 min 34 s) | 4 (6 min 54 s) | api-mail 3B/10T, api-mail inchangé |
| /lint-angular | ok | 1 min 50 s | — | — | — | — |
| /lint-mobile | skipped | 1.9 s | — | — | — | client-mobile inchangé depuis 5583857 (lint vert) |
| /e2e | ok | 17 min 41 s | — | — | — | e2e ×19 (1 h 35 min), après sync develop |
| /review | ok | 1 min 58 s | 15 (7 min 13 s) | 15 (34 min 54 s) | — | api-mail 5B/5T, client-mobile 5B/5T, client-angular 5B/5T, 5e passage, PRs ouvertes |
| /tech-writer | ok | 1 min 22 s | — | — | — | — |
| /merge | ok | 5 min 37 s | — | — | — | — |
| **Total cycle** | | **34 min 26 s** | **36 (24 min 45 s)** | **46 (1 h 30 min)** | **4 (6 min 54 s)** | |

Autres commandes mesurées : lint ×7 (7 min 22 s), restore ×1 (3 min 18 s)

## Develop log

- Repos touched : api-mail (pushed), client-mobile (pushed), client-angular (code-only, non commité sur `feature/nova-mss-weda-integration`)
- DTOs published : no DTO change (aucune branche dtos-mss). Interop : no change.
- Commits :
  - api-mail : `be748778` test(e2e) catalogue (COMPOSE-004, DRAFT-003, DETAIL-001 v3) · `322db0c0` fix(draft) remise incertaine d'un brouillon en 503 `MAIL_DELIVERY_UNCERTAIN` · `0bcf48ff` test(mail) transfert par référence de deux homonymes, trois chemins d'envoi · `02d9472a` refactor(draft) simplify pass · `76b0935b` test(e2e) libellé DRAFT-003 (mobile : « en fermant la rédaction »)
  - client-mobile : `92c6158` fix(mobile) rédaction (remise incertaine, brouillon, homonymes, refus lisibles, envois en attente) · `9df7514` test(mobile) e2e · `2327bb0` refactor(mobile) simplify pass
  - client-angular : non commité (code-only) — voir la liste plus bas
- **Écart à la DOD, assumé** : « le 502 de la route brouillon » n'existe plus pour une remise incertaine. api-mail la rend désormais en 503 problem+json `code: MAIL_DELIVERY_UNCERTAIN`, comme sendmail. Le 502 ne reste que pour « rien n'est parti » (serveur injoignable), qui reste renvoyable. Les deux clients lisent le code, plus le statut 0 et le 504. Raison : traiter tout 502 comme « peut-être parti » aurait bloqué le renvoi d'un message qui n'est jamais parti.

### client-angular (weda2) — défauts corrigés
- ANG-14 : remise incertaine reconnue (`isDeliveryUncertain` : 503 code, 0, 504), `detail` serveur affiché (`compose-send-uncertain`), « Envoyer » et Ctrl+Entrée bloqués. Envois en attente : `deliveryUncertain` affiché, ligne non renvoyable, exclue de « Tout envoyer », la série s'arrête.
- ANG-15 : le contexte annule-et-remplace voyage dans `ComposePrefill.cancelAndReplace` ; le signal partagé `MailEventService.cancelAndReplaceContext` est supprimé. `warning` de la réponse affiché.
- ANG-16 : identifiant de brouillon adopté seulement après création (`proposedDraftId` / `persistDraft`), `PUT` 404 → `POST` du même id. Fermeture qui échoue → rédaction ouverte + `DRAFT_SAVE_FAILED_MESSAGE`. 404 à l'envoi du brouillon → sendmail.
- ANG-17 : chemin unique `saveThen` pour fermer ou remplacer (autre message, « Nouveau message », brouillon de la liste ; intention : abandon demandé). `beforeunload` tant qu'il reste du non-enregistré. Une signature seule n'est pas du contenu.
- ANG-18 / ANG-19 : transfert par référence (`sourceFolderPath/sourceUid/sourceOccurrence`), plus aucun téléchargement donc plus rien en attente à l'envoi. Lecture : téléchargement et aperçu avec `occurrence`, clé de ligne `attachmentKey` (homonymes distincts). `homonymRanksOf` déplacé dans `core/utils/attachment-occurrence.util.ts` (réutilisé par l'import Weda).
- ANG-26 : `failedActionsCount` exposé par `MailboxSessionStore` et affiché ; une confirmation partie n'est plus annulée en quittant la page.
- ANG-42 / ANG-43 : `compose-body.util.ts` (`withTemplate`, `withSignature`, `hasSignature`) — modèle et signature placés par rôle, au-dessus de la citation, avant comme après la première frappe ; un brouillon rouvert ne reçoit pas de seconde signature.
- ANG-44 : adresse tapée sans Entrée ajoutée à l'envoi (ou envoi refusé, message `compose-address-error`), syntaxe vérifiée, Cc/Cci non vides non masquables.
- ANG-45 : `detail` serveur affiché pour 400 / 409 ; la limite de taille compte les fichiers en cours de lecture.
- ANG-46 : un brouillon d'annule-et-remplace rouvert reste un annule-et-remplace, en ligne comme sans carte.
- ANG-75 : autosave relancé après échec (et dit) ; contact sans adresse principale ajouté par son adresse MSSanté ; aperçu de correction remis à zéro ; modèles et signatures : pas de double création, échecs dits, réponse IA écartée si le modèle a changé, « par défaut » appliqué sur l'état courant ; dialogue des doublons : acquittement redemandé à chaque ouverture.
- Hors périmètre, restant : le PDF d'un CDA (`mail-body`, `medical-document-modal`, `mail-read-only-view`) se télécharge encore par nom seul (homonymes de CDA, à reprendre avec `cdaPdfRank`). Mobile : `medical-document-modal` idem.

### Fichiers Angular modifiés (non commités, à commiter par l'humain sur TFS)
`front/e2e/mss-e2e/specs/functional.e2e.ts`, `front/e2e/mss-e2e/support/e2e-backend.ts`, `libs/mss/src/core/models/{mail,pending-email,sync}.model.ts`, `core/stores/mailbox-session.store.ts`, `core/utils/problem-details.utils{,.spec}.ts`, nouveaux `core/utils/{compose-body,attachment-occurrence,mail-address-syntax}.util{,.spec}.ts`, `features/mail/components/mail-compose/*` (composant, template, scss, 5 specs dont le nouveau `mail-compose-safety.component.spec.ts`), `mail-detail.component{,.spec}.ts`, `mail-attachment.component.{ts,html,spec.ts}`, `duplicate-cleanup-dialog.component{,.spec}.ts`, `weda-import.utils.ts`, `services/mail-event.service.ts`, `features/pending-sends/*`, `features/signatures/*` (+ spec neuf), `features/templates/*` (+ spec neuf).

> ⚠️ **À commiter sur TFS AVANT le merge de la PR api-mail** (conventions/e2e.md, « test-angular-non-commite ») : `functional.e2e.ts` porte E2E-COMPOSE-004 v1, E2E-DRAFT-003 v1 et E2E-DETAIL-001 v3, requis côté angular.

### Preuves rouges
- Unitaires weda2, par mutation (marqueur compté, restauré), chaque fois rouge sur le test visé :
  - M1 remise incertaine (4 rouges ANG-14) · M2 contexte hérité (ANG-15) · M3 PUT sur id jamais créé (8 rouges ANG-16/17) · M4 remplacement sans enregistrement (4) · M5 occurrence ignorée (ANG-18) · M6 adresse tapée ignorée (2) · M7 `detail` masqué (4, ANG-45) · M8 modèle qui écrase (ANG-42) · M9 signature repérée par commentaires (2, ANG-43) · M10 Cc masquable.
  - P1–P5 envois en attente. P5 a d'abord survécu (un 503 arrêtait déjà la série) : test durci au statut 0 et au 504, rouge ensuite.
  - R1–R3 lecture des homonymes · T1–T4, S1–S2, D1 modèles, signatures, doublons.
- E2E weda2 (banc `--serve-only`, nouveau bundle attendu + 15 s) :
  - E1 remise incertaine neutralisée → COMPOSE-004 rouge sur « le praticien lit que le message est peut-être parti ».
  - E2 fermeture sans enregistrement → DRAFT-003 rouge sur l'attente du `POST /drafts`.
  - E3 occurrence ignorée → DETAIL-001 rouge sur « porte les deux scan.pdf, chacun avec son contenu ».
  - Témoins restaurés rejoués : COMPOSE-001/003/004, DRAFT-001/002/003, DETAIL-001 verts (7/7).
- api-mail (agent) : `ADraftWhoseSendThrows_GoesBackToEditing_UncertainIs503Typed_OtherwiseIs502WithTheCause`, `ADraftSendThatFails_IsClassifiedByItsStage_ByTheRealSmtpService` (vrai SmtpService, 4 stades), `AForwardOfTwoHomonymParts_ByReference_DeliversBothContents` (sendmail, brouillon, mis de côté puis confirmé ; relu dans GreenMail). Exactement 6 rouges sous mutations (502 d'avant ; occurrence forcée à 0).
- Mobile (agent) : 19 + 1 + 2 rouges unitaires sous mutation. **E2E mobile écrits mais non joués sous mutation** (banc partagé avec l'agent api-mail) : à jouer par `/e2e`.

### Build, tests, qualité
- api-mail : build 0 erreur ; suite complète domain 195, infrastructure 690, application 3 670, integration 908/924 (16 ignorés IA), api 1 275/1 276. L'unique rouge, `E2eUnattachedXdmTests.TheSeededCda_CarriesATrappedCell…`, passe seul (6/6) : instabilité sous charge, sans rapport avec le diff.
- client-mobile : build vert, 1 147/1 147, eslint propre.
- client-angular : `npm run build` vert ; `npm test` vert sur les 12 projets (mss 1 924, weda2 2 653…) ; eslint 0 erreur sur les fichiers touchés.
- Passe qualité (/simplify) :
  - Applied & committed : api-mail `02d9472a` ; client-mobile `2327bb0`.
  - Applied (code-only, uncommitted) : client-angular — `deliveryUncertainMessage` et `describeSendError` réutilisent `serverDetail` ; instantané du brouillon sans le base64 des pièces, calculé une fois par enregistrement ; compteur d'octets en lecture en nombre simple ; règle d'arrêt de « Tout envoyer » factorisée (`stopsSendAll`). Revalidé : build + `npm test` verts.
  - Écartés (changement de comportement ou hors diff) : toujours `POST` en upsert au lieu de `PUT` ; rang d'homonyme posé une fois au chargement du `MailDto` ; requêtes d'envoi non annulables au niveau de `MssApiService` ; clés de dédoublonnage unifiées ; style d'erreur commun modèles/signatures.
- Environnement : `apps/weda2/src/app/core/api/generated/` (client hey-api ignoré par git, généré en mai sur `nova-rewriting`, sans son `hey-api.config.ts` sur la branche actuelle) cassait toute compilation de weda2. **Déplacé, pas supprimé**, dans `C:\Users\pascal.cabanel\AppData\Local\Temp\claude\d--TechWatch-HealthPlatform\172da0fb-2fad-4fac-9853-14ed682a3f50\scratchpad\weda2-api-generated-backup\generated`.
- Prévention (règle d'or) : `conventions/e2e.md` — 3 « trous du filet » ; `conventions/angular.md` — 4 consignes neuves (identifiant-adopte-avant-creation, contexte-pose-a-cote, reponse-sur-instantane, desabonnement-annule-un-envoi), récidives jsdoc (8, ancrage sur `@Component`) et double-incomplet (2).
- DOD self-check : build/tests ✓ ; tests unitaires et de composant de la DOD présents et vus rouges ✓ ; test d'intégration du transfert par référence ✓ ; scénarios E2E-COMPOSE-004, DETAIL-001 v3, DRAFT-003 au catalogue et dans les deux clients ✓ ; trous du filet ✓ ; aucune donnée de santé ajoutée aux journaux ✓ (aucun log ajouté côté clients).
- Next step : /sonar task-376

## Sonar log

- Serveur : SonarQube 25.6.0 (`sonar.token`), conteneurs redémarrés (`sonarqube_db` puis `sonarqube`). Deux analyses complètes de la branche (build Release + 5 passes OpenCover, toutes vertes).
- Phase 1 (new code, fichiers de la task) : ✓ — 1 issue trouvée et corrigée (S103, ligne de 157 caractères dans le commentaire de `DraftService.SendThroughOutgoingAsync`, héritée de task-330 mais dans un fichier de la task), commit `6ecb8e29`. **0 issue new-code restante dans les fichiers de la task**, new_coverage = 98,2 %.
- Quality Gate du projet : **ERROR, sans dette introduite par la task** (mémoire « new-code period inclut des tasks déjà mergées ») :
  - `new_violations` 72 : aucune dans les fichiers de la task. Les trois issues récentes viennent de task-384/385 (`MeteredChatCompletionService.cs:82` S134, `AiCallRecorder.cs:63` S103, `BuildInfoProvider.cs:53` S4049), le reste d'avant.
  - `new_security_hotspots_reviewed` 0 % : 13 hotspots, aucun dans les fichiers de la task (Dockerfile, scripts k6 `tests/loadtest-k6`, `BaseRepository.cs:754`).
- Phase 2 (legacy) : non jouée (optionnelle, best-effort) — la PR porte déjà trois dépôts ; la dette héritée ci-dessus mérite une task dédiée.
- Tests ajoutés par /sonar : 0 (couverture du new code déjà ≥ 95 %).
- `conventions/csharp.md` : non alimenté — la seule règle corrigée (S103) l'a été sur une ligne écrite par task-330, pas par ce /develop.
- ⚠️ **Fuite de secret constatée et stoppée** : `Tools/timing/measure.sh` enregistrait la commande mesurée telle quelle, donc `sonarscanner … /d:sonar.token=squ_…` dans `metrics/timings.jsonl` (versionné, poussé). **204 lignes** contenaient le jeton, sur au moins dix tasks précédentes. Correctif : `redact_secrets` (`Tools/timing/lib.sh`) appliqué par `measure.sh`, journal local masqué (204 → 0, JSON relu valide), vérifié sur la seconde analyse (`sonar.token=***`). **L'historique git du plan de contrôle garde le jeton : sa rotation est à faire par l'humain.**
- Build / tests : ✓ green.

### KPIs qualité (baseline → final)

| Métrique | Baseline (analyse du 14/10) | Final (branche task-376) | Δ |
|---|---|---|---|
| Quality Gate (new code) | ERROR | ERROR | → (hérité, 0 dans les fichiers de la task) |
| New coverage | 98,1 % | 98,2 % | +0,1 pt |
| New violations | 70 | 72 | +2 (task-384/385, hors task) |
| Bugs | 2 | 2 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 15 | 15 | 0 |
| Code smells | 68 | 70 | +2 (hors task) |
| Coverage (projet) | 97,9 % | 98,0 % | +0,1 pt |
| Duplication | 0,3 % | 0,3 % | 0 |
| Reliability / Security / Maintainability | D/A/A | D/A/A | → |

## Lint log

- client-angular : `nx affected -t lint --base=origin/next --head=HEAD --projects=tag:scope:mss` → **0 erreur** (avertissements seulement : max-lines, complexity, `@example` vides antérieurs). Aucune itération nécessaire (0/5).
- ESLint ciblé sur les fichiers touchés par /develop, e2e compris : 0 erreur (fait en /develop, avant et après la passe qualité).
- Build `npm run build` et `npm test` (12 projets) verts sur cet arbre, revalidés après la passe qualité ; aucune modification depuis.
- Code-only : aucune opération git.

## Lint mobile log

- client-mobile : `npm run lint` → « All files pass linting. » Aucune itération (0/5), aucun commit. Build et tests (1 147/1 147) verts au /develop, arbre inchangé depuis (`2327bb0`, poussé).

## E2E log

| Voie | Jouée | Résultat | Durée |
|---|---|---|---|
| mobile | `npm run e2e:headless` (api-mail + client-mobile touchés) | 40 verts, 0 flaky, 0 rouge — parité verte | ~11 min |
| angular | `npm run e2e:mss` (api-mail + client-angular touchés) | 47 verts, 1 flaky, 0 rouge — parité verte | ~8 min |

- **Premier passage mobile rouge (3)**, corrigé dans les tests neufs de la task (commit mobile `af9e476`) puis voie rejouée entière :
  - E2E-COMPOSE-004 : `toBeDisabled()` ne lit pas un `ion-button` (bouton pourtant désactivé) → état lu sur `aria-disabled` ; même défaut, en vert qui ment, dans E2E-COMPOSE-003 (`toBeEnabled()` toujours vrai), durci.
  - E2E-MAIL-004, E2E-AI-001 : lignes seedées sorties de l'écran par les transferts laissés dans l'INBOX par E2E-DETAIL-001 v3 → les deux clients suppriment désormais leurs transferts en fin de parcours.
  - Préventions : `conventions/e2e.md` « etat-desactive-d-un-ion-button » (nouvelle) et « inbox-laissee-en-l-etat » (2ᵉ occurrence, après task-340).
- **Preuves par mutation mobile** (banc `--serve-only`) : MM1 remise incertaine neutralisée → COMPOSE-004 rouge sur « Envoyer est désactivé » ; MM2 fermeture sans enregistrement → DRAFT-003 rouge sur « le brouillon est enregistré côté serveur » ; MM3 occurrence forcée à 0 → **non concluant** (deux essais rouges sur l'arrivée du message déposé, avant le point muté ; témoin restauré vert) — la règle reste prouvée par le test unitaire mobile et le test d'intégration api-mail. Témoins COMPOSE-003/004, DRAFT-003, DETAIL-001 verts.
- Quarantaine E2E-COMPOSE-002 (angular) : 13 jours (posée le 2026-10-09), sous le seuil de 14 jours ; passée verte.
- Flaky inscrit au registre : E2E-SEARCH-001 (angular), 1ʳᵉ occurrence.
- Démontage vérifié : ports 4200 / 8100 libres, aucun conteneur e2e résiduel.
- Écrans modifiés sans spec e2e modifié : envois en attente, modèles, signatures, dialogue des doublons (weda2) et envois en attente (mobile) — couverts par des tests de composant, pas par un parcours.

### Porte

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « recherche — requête et recherche avancée » (E2E-SEARCH-001)

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ⚠️ flaky | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Code Review Summary

**Verdict : CHANGES REQUESTED** — détail et correctifs attendus dans `questions/task-376.md`. Aucune PR ouverte.

- Validation (/review) : api-mail build ✓, tests 195 + 690 + 3 670 + 1 276 + 908/924 (16 ignorés IA), 0 échec ; client-mobile build ✓, 1 147/1 147 ; client-angular (`feature/nova-mss-weda-integration`, 44 fichiers non commités) build ✓, `npm test` ✓.
- E2E double verrou : `## E2E log` vert ✓.
- api-mail : ✅ APPROVED. Règle 1b : remise incertaine du brouillon → `ADraftWhoseSendThrows_…(true)` et `ADraftSendThatFails_IsClassifiedByItsStage_ByTheRealSmtpService` (rouges sous mutation « 502 d’avant ») ; transfert par référence de deux homonymes → `AForwardOfTwoHomonymParts_ByReference_DeliversBothContents` × 3 chemins (rouges sous « occurrence forcée à 0 »).
- client-mobile : ❌ B1 brouillon orphelin si Envoyer pendant l’autosave ; B2 seconde pièce homonyme illisible (dédoublonnage de `mergedAttachments`, tests qui contournent le parent) ; B3 fermeture par geste qui agit sur la rédaction rouverte.
- client-angular : ❌ B1 (même course, plus le repli `404 → POST` qui recrée le brouillon consommé).
- Préventions : `conventions/angular.md` — revers de « identifiant-adopte-avant-creation », nouvelle « tester-a-travers-le-parent ».

## Develop log — reprise après /review (CHANGES REQUESTED)

- **B1 (weda2 et mobile)** — un enregistrement de brouillon en vol au moment d'« Envoyer » ne laisse plus de brouillon du message parti : un compteur d'envois engagés est relevé au départ de chaque enregistrement ; s'il a bougé au retour, la réponse est ignorée, un brouillon tout juste créé est retiré (`deleteDraft`), et le repli `404 → POST` n'a plus lieu. L'enregistrement automatique reprend normalement après un envoi en échec.
  - weda2 : `mail-compose.component.ts` (`sendsDispatched`, `persistDraft`, `discardOrphanDraft`, `saveDraftNow` en `finalize`). Tests `mail-compose-safety.component.spec.ts` « enregistrement en vol pendant l'envoi (revue B1) » : **2 rouges sur le code revu** (`deleteDraft` jamais appelé ; `saveDraft` rappelé après le 404), verts après ; témoin « l'autosave reprend après un échec » vert avant et après.
  - mobile : `aa037b6` — 2 tests B1 rouges d'abord (`deleteDraft('late-1')` absent et id adopté ; `saveDraft` appelé 2 fois), témoin autosave vert.
- **B2 (mobile)** — `mail-detail.mergedAttachments` garde deux pièces MIME homonymes (clé `attachmentRowKey`, rang à partir de la seconde) ; la pièce médicale de même nom que la première reste fusionnée. `4c6a92f` — test par `mergedAttachments` puis `?occurrence=1`, rouge d'abord (`Expected $.length = 1 to equal 2`). Consigne appliquée : « tester-a-travers-le-parent ».
- **B3 (mobile)** — une ouverture demandée pendant la fermeture (qui enregistre) attend l'issue de l'enregistrement ; en cas d'échec, l'ancienne rédaction revient avec son contenu et le message, l'ouverture en attente est abandonnée ; garde de session en défense. `aa037b6` — 2 tests rouges d'abord (réouverture restée fermée ; contenu « Ancien » perdu).
- Suggestions de revue traitées au passage (weda2) : analyse HTML **inerte** dans `compose-body.util.ts` (`DOMParser` au lieu d'un `div` du document vivant ; non testable en jsdom, qui ne charge pas les images) ; message d'échec des modèles et signatures effacé à la sélection, à la création et à la fermeture (test `anErrorMessage_FollowsTheTemplateItConcerns`).
- Validation : weda2 `npm run build` ✓, `npm test` ✓ (12 projets) ; eslint 0 erreur ; mobile build ✓, 1 154/1 154, eslint propre, passe qualité sans changement. api-mail inchangé.
- Fichiers weda2 de la reprise (toujours non commités, code-only) : `mail-compose.component.ts`, `mail-compose-safety.component.spec.ts`, `compose-body.util.ts`, `mss-templates.component{,.spec}.ts`, `mss-signatures.component.ts`.
- Next step : /sonar task-376 (api-mail inchangé depuis la dernière analyse → skip mesuré), puis /lint-angular, /lint-mobile, /e2e (deux voies rejouées), /review.

- Sonar (reprise) : skipped — api-mail inchangé depuis la dernière analyse (`6ecb8e29`), KPIs ci-dessus toujours valables.
- Lint Angular (reprise) : 0 erreur, aucune itération ; build et `npm test` verts au /develop de la reprise, arbre inchangé depuis.
- Lint mobile (reprise) : « All files pass linting. » sur `4c6a92f`, aucune itération.

## E2E log — reprise (après les correctifs B1–B3)

| Voie | Jouée | Résultat |
|---|---|---|
| mobile | `npm run e2e:headless` sur `4c6a92f` | 40 verts, 0 flaky, 0 rouge — parité verte |
| angular | `npm run e2e:mss` (arbre weda2 de la reprise) | 46 verts, 2 flaky, 0 rouge — parité verte |

- Flaky inscrits au registre : E2E-SEARCH-001 (2ᵉ occurrence), E2E-MAILBOX-001 (1ʳᵉ).
- Démontage vérifié : ports 4200 / 8100 libres, aucun conteneur e2e résiduel.

### Porte

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (2) :

- [angular] « recherche — requête et recherche avancée » (E2E-SEARCH-001)
- [angular] « messagerie — changer de boîte depuis l’écran mail, embarqué » (E2E-MAILBOX-001)

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ⚠️ flaky | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ⚠️ flaky | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Code Review Summary — 2ᵉ passage (après reprise B1–B3)

**Verdict : CHANGES REQUESTED** — un bloquant neuf, B4, sur weda2 et mobile (voir `questions/task-376.md`). Aucune PR ouverte.

- B1 (weda2, mobile), B2 et B3 (mobile) : ✅ corrigés, confirmés par la relecture.
- B4 : après un envoi en échec, la suppression du brouillon orphelin peut effacer le brouillon enregistré juste après, l’identifiant proposé n’étant pas renouvelé (une ligne par client).
- Validation : api-mail build ✓, tests verts sauf 1 rouge instable sans lien (`MailClientSessionManagerCoverageTests.AcquireSmtpSlotAsync_WhenCancelledAsTheSlotIsGranted…`, 5/5 vert isolé, code non touché par la task) ; mobile build ✓, 1 154/1 154 ; weda2 build ✓, `npm test` ✓.
- `## E2E log` (reprise) vert.

## Develop log — reprise B4 (2ᵉ passage de /review)

- **B4 (weda2 et mobile)** — quand un brouillon orphelin est retiré, l’identifiant proposé est remis à zéro : l’enregistrement suivant en prend un nouveau, et la suppression ne peut plus effacer le brouillon enregistré juste après.
  - weda2 : `persistDraft` (`proposedDraftId = null` dans la branche « dépassé »). Test « après un orphelin retiré, l’enregistrement suivant propose un nouvel identifiant » rouge d’abord (même identifiant reproposé), vert après.
  - mobile : `5583857` (`pendingDraftId = null`), test B4 rouge d’abord (`Expected … not to be …`) ; commentaire B3 corrigé (l’ouverture en attente est abandonnée sur échec).
- **weda2, suggestion de revue** : l’enregistrement automatique reprend après un envoi en échec (`failSend`), jamais après une remise incertaine. Test « le minuteur d’enregistrement automatique reprend » rouge d’abord, prouvé par le minuteur (et non plus par un appel manuel) ; témoin « reste arrêté après une remise incertaine » vert.
- Validation : weda2 build ✓, `npm test` ✓, eslint 0 erreur ; mobile build ✓, 1 155/1 155, eslint propre.
- Next step : /sonar (api-mail inchangé → skip mesuré), /lint-angular, /lint-mobile, /e2e, /review.
- Sonar (reprise B4) : skipped, api-mail inchangé. Lint Angular et mobile (reprise B4) : 0 erreur, aucune itération.

## E2E log — reprise B4

| Voie | Jouée | Résultat |
|---|---|---|
| mobile | `npm run e2e:headless` sur `5583857` | 40 verts, 0 flaky, 0 rouge — parité verte |
| angular | `npm run e2e:mss` (arbre weda2 de la reprise B4) | 47 verts, 1 flaky, 0 rouge — parité verte |

- Voie Angular tombée deux fois en **outillage** avant de passer : `weda2:serve` ne démarrait pas (« plugin worker … not connected to within 5 seconds », puis « Failed to start plugin worker ») pendant la compilation parallèle du backend e2e ; `nx reset` n'a pas suffi ; jouée verte avec `NX_PLUGIN_NO_TIMEOUTS=true`. Piège consigné en mémoire (outillage).
- E2E-SEARCH-001 : 3ᵉ occurrence flaky → task de stabilisation à ouvrir.
- Démontage vérifié : ports 4200 / 8100 libres, aucun conteneur e2e résiduel.

### Porte

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « recherche — requête et recherche avancée » (E2E-SEARCH-001)

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ⚠️ flaky | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Code Review Summary — 3ᵉ passage (après reprise B4)

**Verdict : CHANGES REQUESTED** — weda2 seul, B5 (voir `questions/task-376.md`). Aucune PR ouverte.

- B4 : ✅ mobile (`5583857`), ✅ weda2 dans l’ordre revu ; reprise de l’autosave après échec : ✅.
- B5 (weda2) : l’enregistrement suivant peut partir **avant** le retour de l’orphelin et reproposer son identifiant (`saveThen` n’attend pas l’enregistrement en vol). Correctif d’une ligne dans `dispatchSend`.
- Validation : api-mail 195 + 690 + 3 670 + 1 276 + 908/924, 0 échec ; mobile 1 155/1 155 ; weda2 build ✓, `npm test` ✓. `## E2E log` (reprise B4) vert.

## Develop log — reprise B5 (3ᵉ passage de /review)

- **B5 (weda2 seul)** — B4 dans l'autre ordre : un enregistrement de fermeture parti avant le retour de l'orphelin reproposait son identifiant. Correctif : `dispatchSend` abandonne l'identifiant proposé (s'il n'y a pas encore de brouillon adopté) au moment où l'envoi est engagé ; tout enregistrement en vol garde alors un identifiant qu'aucun enregistrement suivant ne reproposera, quel que soit l'ordre des retours.
- Test `mail-compose-safety.component.spec.ts` « une fermeture enregistrée avant le retour de l'orphelin prend un autre identifiant » : **rouge d'abord** (`expected '38a0…' not to be '38a0…'`), vert après ; il vérifie aussi que l'orphelin est supprimé et jamais le brouillon de fermeture.
- Validation : 136 tests de rédaction verts ; `npm run build` ✓ ; `npm test` ✓ (12 projets) ; eslint 0 erreur ; formatage conforme.
- api-mail et client-mobile inchangés (`6ecb8e29`, `5583857`).
- Next step : /sonar (skip), /lint-angular, /lint-mobile (skip, inchangé), /e2e (voie Angular rejouée ; rapport mobile du même commit réutilisé), /review.
- Sonar et lint mobile (reprise B5) : skipped, repos inchangés. Lint Angular : 0 erreur.

## E2E log — reprise B5

| Voie | Jouée | Résultat |
|---|---|---|
| mobile | non rejouée : `client-mobile` inchangé depuis `5583857` ; rapport de la voie verte du même commit (reprise B4) réutilisé par la porte | 40 verts, 0 flaky, 0 rouge — parité verte |
| angular | `npm run e2e:mss` (arbre weda2 de la reprise B5, `NX_PLUGIN_NO_TIMEOUTS=true`) | 47 verts, 1 flaky, 0 rouge — parité verte |

- E2E-SEARCH-001 : 4ᵉ occurrence flaky → task de stabilisation à ouvrir.
- Démontage vérifié : ports 4200 / 8100 libres, aucun conteneur e2e résiduel.

### Porte

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « recherche — requête et recherche avancée » (E2E-SEARCH-001)

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ⚠️ flaky | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Code Review Summary — 4ᵉ passage (après reprise B5)

**Revue de code : APPROVED** — B1 à B5 corrigés et confirmés par la relecture (weda2 et mobile). **PR non ouvertes** : la synchronisation avec `develop` (step 8) bute sur un conflit d'identifiant e2e avec task-379 — voir `questions/task-376.md`.

- B5 (weda2) : ✅ — `dispatchSend` abandonne l'identifiant proposé ; quel que soit l'ordre des retours, l'orphelin ne peut plus effacer un brouillon enregistré ensuite (test rouge d'abord).
- Suggestions (task de suivi) : « Nouveau message » pendant un envoi en vol réinitialise la rédaction (préexistant, `openCompose` l. 650) ; `proposedDraftId = null` au retour de l'orphelin devenu redondant ; recréation `404 → POST` revenant après l'envoi (doublon rare, sans perte) ; branche `queued` de `executeSend` probablement morte pour les envois.
- Validation : api-mail build ✓, tests 195 + 690 + 3 670 + 1 276 verts, intégration 905/924 avec **3 rouges préexistants « du jour »** (`FilterTodayEmails…`, `GetFolderTodayAsync…`, `GetFolderNotSeenTodayAsync…`), joués à 01 h 06 heure locale — fenêtre 00 h–02 h connue (mémoire `reference_api_mail_integration_today_tests_utc_midnight`), verts aux trois validations précédentes sur le même commit ; mobile 1 155/1 155 ; weda2 build ✓, `npm test` ✓.
- `## E2E log` (reprise B5) : vert.

## E2E log — après sync develop (task-379 + task-386, scénario renuméroté E2E-COMPOSE-005)

| Voie | Commande | Résultat |
|---|---|---|
| mobile | `npm run e2e:headless` sur `a087b45` (api-mail `f1976f5d`) | 41 passed (6.9m) — 41 verts, 0 flaky, 0 rouge, parité verte |
| angular | `npm run e2e:mss` (arbre weda2 de l humain après merge task-379/386, `NX_PLUGIN_NO_TIMEOUTS=true`) | 48 passed (7.3m) — 48 verts, 1 flaky, 0 rouge, parité verte |
| gate | `mss.mail.e2e gate` sur le catalogue de la branche fusionnée | code 0 |

Démontage vérifié : aucun conteneur e2e résiduel, ports 5052/3993/3465/3143 libres.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**Flaky (vert au second essai, non bloquant)** (1) :

- [angular] « recherche — requête et recherche avancée » (E2E-SEARCH-001)

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ⚠️ flaky | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Code Review Summary — 5ᵉ passage (après sync develop)

**Revue de code : APPROVED** — le blocage du 4ᵉ passage (collision E2E-COMPOSE-004 avec task-379) est levé : le scénario de la task devient **E2E-COMPOSE-005** au catalogue et dans les deux clients. `questions/task-376.md` est retiré.

- Delta relu depuis le 4ᵉ passage : résolutions de merge uniquement.
  - api-mail : catalogue (004 = task-379, 005 = task-376).
  - mobile : `http-error.util.ts` (helpers task-376 + `isDirectoryUnavailable` de task-386 ; l'ancien `sendErrorMessage` de develop est remplacé par celui de la task, qui garde la branche task-354), imports rxjs, spec e2e.
  - weda2 : merges task-379 et task-386 faits par l'humain.
  - Les suggestions multi-adresses de task-379 ne touchent pas le chemin d'envoi.
- Validation sur les arbres fusionnés :
  - api-mail : build ✓, tests 195 + 695 + 3 603 + 1 277 + 963/979 (16 ignorés IA), **0 échec** ;
  - client-mobile : build ✓, 1 190/1 190, lint propre ;
  - weda2 : build ✓, `npm test` ✓ (1 576 tests).
- `## E2E log — après sync develop` : vert (mobile 41/41, Angular 48 + 1 flaky E2E-SEARCH-001), parité verte.
- Règle 1b : inchangée depuis le 1ᵉʳ passage (voir PR api-mail).

## PRs

- api-mail : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/306 — label `awaiting-human-merge`
- client-mobile : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/100 — label `awaiting-human-merge`
- client-angular : code-only — commité et poussé sur TFS par l'humain (`feature/nova-mss-weda-integration` : `80103559` task-376, `174ec2d2` merge task-379, `4e8876a7` merge task-386). L'humain ouvre la PR TFS. Arbre propre au moment de la revue.

## Merged

- 2026-10-23, après test humain (`--i-tested`).
- api-mail #306 : squash `8e7477a8` sur `develop` ; CI « Build and Publish » verte.
- client-mobile #100 : squash `8aaa0a9f` sur `develop` ; CI « Android Build » verte.
- Branches `fix/task-376-redaction-sans-perte-ni-double-envoi` supprimées (distantes et locales) ; clones revenus sur `develop`.
- client-angular : code-only, géré par l humain sur TFS.
