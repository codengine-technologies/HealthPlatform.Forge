# todo-task-138.md — Garde-fous d'envoi conformes sur mobile (INS, opposition, PJ)

**Repos**: client-mobile
**Dependencies**: —
**Epic**: E012

## Objective

Porter sur le compose mobile les **garde-fous d'envoi** présents dans
`client-angular` (`mail-compose`) et absents du mobile, qui relèvent de la
conformité MSSanté/Ségur plus que du confort :

1. **Validation INS destinataire patient** : destinataire `@patient.mssante.fr`
   détecté → `validatePatientIns` ; INS **non qualifiée → envoi bloqué** avec
   message explicite ; INS qualifiée → **dialog de confirmation d'identité**
   (nom, prénom, date de naissance) avant envoi.
2. **Avertissement opposition patient** : opposition active (`getPatientOpposition`)
   → bandeau d'avertissement **non bloquant**.
3. **Case « Bloquer la réponse du patient »** (task-026) : visible uniquement
   quand au moins un destinataire Mon Espace Santé est présent.
4. **Rappel de pièce jointe oubliée** (task-084) : corps évoquant une PJ
   (« ci-joint », « pièce jointe », « PJ », « en annexe », « veuillez trouver » —
   insensible casse/accents) sans fichier joint → dialog « Envoyer quand même ? ».
   Porter `attachment-reminder.util.ts` tel quel.
5. **Limite de taille des PJ + jauge** : taille totale max (défaut 10 Mo,
   surchargée par les settings utilisateur), jauge de remplissage, blocage
   d'ajout au-delà.

US **frontend-only** : tous les endpoints existent (`validatePatientIns`,
`getPatientOpposition`, `getUserSettings`, champ de blocage réponse dans le
DTO d'envoi). Aucun changement backend ni DTO.

## Parité Angular — sources à porter

- `libs/mss/src/features/mail/components/mail-compose/` (validations d'envoi)
- `libs/mss/src/features/mail/utils/attachment-reminder.util.ts`
- `MssApiService` mobile : + `validatePatientIns(ins)`, réutiliser
  `getPatientOpposition(ins)` (déjà présent depuis task-132).

## Definition of Done

- [ ] Build passe (`npm ci && npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] Envoi vers patient à INS non qualifiée **bloqué** avec message FR explicite
- [ ] INS qualifiée → dialog de confirmation d'identité avant envoi (annulable)
- [ ] Opposition active → bandeau d'avertissement non bloquant affiché
- [ ] Case « Bloquer la réponse du patient » visible **uniquement** avec destinataire MES ; valeur transmise à l'envoi
- [ ] Rappel PJ oubliée : dialog de confirmation ; aucun avertissement si un fichier est joint ; tests unitaires du util (mots-clés, casse, accents)
- [ ] Jauge de taille PJ + blocage au-delà de la limite (settings ou défaut 10 Mo)
- [ ] Tests unitaires : validation INS (qualifiée/non qualifiée/erreur), visibilité case MES, limite PJ
- [ ] Libellés FR en dur ; `data-testid` sur dialogs, bandeau, case, jauge
- [ ] Aucun trait patient/INS dans les logs client

## Manual Test Plan

- `cd Client/Mobile && npm start` ; compose un message
- Destinataire patient MES à INS qualifiée → dialog d'identité, confirmer → envoi OK
- Destinataire patient à INS non qualifiée → envoi bloqué, message explicite
- Patient avec opposition active → bandeau visible, envoi toujours possible
- Cocher « Bloquer la réponse du patient » (visible seulement avec destinataire MES) → envoi OK
- Écrire « veuillez trouver ci-joint » sans PJ → dialog « Envoyer quand même ? » ;
  joindre un fichier → plus d'avertissement
- Joindre des fichiers jusqu'à dépasser la limite → jauge rouge, ajout bloqué

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR nouvelle — portage de garde-fous déjà référencés (tasks 026, 084)
- **Exigences DSR honorées** : identito-vigilance à l'envoi (INS qualifiée exigée pour adresser un patient) — parité avec l'exigence déjà honorée côté web
- **INS** : **INS qualifiée exigée** pour l'envoi à un patient MES ; non qualifiée → blocage. Validation via endpoint existant ; INS jamais en log/URL client
- **Authentification PS** : session e-CPS/PSC existante — l'envoi MSSanté reste sous authentification forte (garde-fou métier)
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — pas de nouveau format d'échange
- **Tracé PGSSI-S** : envoi journalisé côté `api-mail` (canal existant) ; aucun log client des traits
- **Consentement patient** : l'avertissement d'**opposition** matérialise le respect du choix du patient au moment de l'envoi
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — backend existant
- **AIPD / impact RGPD** : inchangé

## Branches
- `client-mobile` (pushed) : feat/task-138-compose-send-guards — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-138-compose-send-guards

## Stitch design log

- Project : client-mobile (id 10088502293310567548)
- Screens :
  | Component / Page | Stitch title | Screen id | Action | Screenshot |
  |---|---|---|---|---|
  | mail-compose (garde-fous d'envoi : dialogs INS/PJ, bandeau opposition, case MES, jauge PJ) | mail-compose | 340f18be9395435f8fc472e0c476f736 | reused | https://lh3.googleusercontent.com/aida/AP1WRLvyMPn0Tx43j94UDZ5P-9z1pkfxN9mtioVW-_1NB035wUscDInZxdza3wb9h3T6h3vZ0DzaIpTF6v9UisVvqByDZ7AbY-XQmBenh9sRqvlilCosCE0T69Pn9c6lxllpxHx3Xq20rvHNzfoMqCn0YscFuntgCX60s39yhpGZLm6mrx5vV0csP-GwbtU33zo0Uqhh0aB-2XIX4I9Ldph4yWvs9fiR1tigeRJsLmvsLuMYw8IIR8y6ipXfgx7u |
- Note : pas de nouvel écran — les garde-fous s'insèrent dans l'écran compose existant ; les dialogs (confirmation d'identité, rappel PJ) suivent les patterns modaux du design system « Clinical Precision » déjà en place (cf. biology-ack-confirm-dialog, patient-attachment-dialog).
- ⚠ Rename / labelliser in Stitch UI : none
- ⚠ Doublons suspectés à nettoyer dans l'UI : ceux de task-137 (déjà signalés)
- Stitch reachable : ✓

## Develop log

- Repos touched : client-mobile (US frontend-only)
- DTOs published : no DTO change
- Interop published : no interop change
- Commits :
  - client-mobile : 2b3e3a0 feat(mobile): garde-fous d'envoi conformes dans le compose (task-138)
- Local build / test : ✓ `npm run build` 0 erreur ; `npm test -- --watch=false --browsers=ChromeHeadless` 331/331 SUCCESS (+28)
- DOD self-check : 11/11 items vérifiables par commande vérifiés
  - build ✓, tests ✓, blocage INS non qualifiée + message FR ✓ (testé),
    dialog identité annulable ✓ (confirm + cancel testés), bandeau opposition
    non bloquant ✓ (testé, envoi possible), case MES visibilité + payload +
    auto-reset ✓ (testés), rappel PJ + util porté tel quel + tests
    mots-clés/casse/accents ✓, jauge + blocage limite (settings/10 Mo) ✓
    (testés), FR en dur + data-testid (dialogs, bandeaux, case, jauge) ✓,
    aucun trait/INS loggé ✓ (0 console.*)
  - validation visuelle end-to-end : deferred to manual test (HAG)
- Choix documenté : opposition = bandeau **non bloquant** (contrat DOD/Manual
  Test Plan de la task), là où Angular utilise un confirm bloquant — divergence
  volontaire du PO
- Next step : /forge-simplify task-138

## Simplify log
- Repos passed : client-mobile
- Applied & committed : client-mobile: 5 files (6eb8e0e)
  - reuse : `formatFileSize` extrait en `core/utils` (doublon avec `mail-attachment.formatSize`, les 2 composants consomment l'util)
  - altitude : `mss-address.util` (`isPatientMssAddress`/`extractInsFromPatientAddress`, règles pures + 3 tests) ; resolver de dialog libéré défensivement (pas de promesse orpheline)
  - simplification : clé d'opposition en `computed patientInsKey` (supprime champ mutable + garde manuel + reset)
  - efficiency : `refreshOppositionWarnings` parallélisé (Promise.all)
- No change (skips motivés) : réécriture des dialogs de confirmation en `AlertController` (le DOD exige des `data-testid` sur dialogs et boutons, message d'identité multi-ligne pre-line, mécanisme testé au vert — candidat d'harmonisation ultérieure hors task) ; parallélisation `validatePatientIns`+`getPatientByIns` (fetch de fiche inutile quand l'envoi est bloqué — l'agent efficiency la notait lui-même basse confiance)
- Rolled back (validation RED) : none
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Build / tests : ✓ `npm run build` 0 erreur ; 334/334 tests SUCCESS (+3)
- Incident tooling : le 1er agent simplification a diffé le repo racine de la forge (mauvais cwd) — relancé avec `git -C Client/Mobile`, findings pris en compte

## Lint mobile log
- Baseline : 0 error / 0 warning — « All files pass linting »
- Iterations : 0 (rien à corriger)
- Fixes committed : none
- Residual : none
- Build / tests : inchangés depuis la passe simplify (build ✓, 334/334 ✓)

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/42 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : **APPROVED** (après correction du blocking)
- 14 fichiers reviewés (diff complet vs origin/develop), review indépendante « second développeur »
- Blocking corrigé (df07810) : **course au double envoi** — pas de garde anti-réentrance sur la chaîne de garde-fous asynchrone ; un double-tap pendant la validation INS pouvait envoyer deux fois le même email médical (chemin fallback « validation indisponible »). Garde `sendGuardActive` + test de réentrance (Subject en vol, 2 taps → 1 sendMail)
- Durcissements non bloquants appliqués : dédoublonnage des avertissements d'opposition (clés @for uniques, NG0955) + jeton de version anti-réponses tardives ; libération des dialogs en attente sur close()/reset() ; timer bandeau INS suivi ; maxAttachmentSizeBytes ≤ 0 → défaut 10 Mo ; reader.onerror
- Validation finale : build ✓ (0 erreur), 335/335 tests ✓, lint ✓
- Commits : 2b3e3a0 (feat), 6eb8e0e (refactor /simplify), df07810 (fix review)

## Merged
- Date : 2026-07-06
- `client-mobile` : PR #42 squash-merged — commit `7f36d61` sur develop
- Remote branch `feat/task-138-compose-send-guards` supprimée (locale conservée)
- develop CI : https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/28807445070
