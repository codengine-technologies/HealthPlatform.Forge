# todo-task-137.md — Rattachement email→patient sur mobile

**Repos**: client-mobile
**Dependencies**: —
**Epic**: E012

## Objective

Porter sur `client-mobile` le **rattachement manuel d'un document médical à un
patient existant**, en miroir structurel de `client-angular`
(`patient-attachment-dialog`, task-012). Quand un email porte un document CDA
dont l'INS n'est pas qualifiée (document non rattaché), le détail du mail
affiche un **bandeau « Document non rattaché »** ; le médecin ouvre une modale
de **comparaison visuelle** : traits du CDA (nom, prénom, date de naissance,
sexe) face aux **candidats classés par score de similarité** (max 10, score
[0,1] affiché en %), et rattache le document au patient choisi.

US **frontend-only** : endpoints existants consommés par `client-angular`
(`GET /api/v1/Patients/match`, `POST /api/v1/medical-documents/{documentId}/attach-patient`).
Aucun changement backend ni DTO.

**Garde-fous métier (non négociables)** :
- **Jamais de « Créer un nouveau patient »** — aucun candidat → seule action
  « Ignorer » (parité stricte Angular, mémoire task-012).
- Un document à la fois.
- Traits patient (INS/NIR, nom, date de naissance) jamais loggés côté client,
  jamais dans une URL/route mobile.

## Composants à porter (noms identiques à client-angular)

| Sélecteur | Rôle |
|---|---|
| `mss-patient-attachment-dialog` | Modale Ionic : traits CDA vs liste candidats scorés, « Rattacher » par candidat, « Ignorer » |
| Bandeau dans `mail-detail` | État « non rattaché » → CTA d'ouverture de la dialog ; rafraîchit l'état du document après succès |

`MssApiService` mobile : + `matchPatientByTraits(lastName?, firstName?, birthDate?, gender?)`
et `attachDocumentToPatient(documentId, patientId)` (mêmes signatures qu'Angular
`mss-api.service.ts:1252` / `:1280`).

## Comportement attendu (parité Angular)

- Détail d'un mail porteur d'un document CDA non rattaché → bandeau visible.
- Ouverture dialog → colonne traits CDA + liste candidats triés par score
  décroissant (affichage %), identité complète par candidat.
- « Rattacher » → POST, toast succès, bandeau disparaît sans rechargement
  complet, timeline patient à jour au prochain affichage.
- Aucun candidat → message « Aucun candidat » + « Ignorer » seul.
- Erreurs (400 sans trait, 404, réseau) → toast lisible via `extractProblemDetail`.

## Definition of Done

- [ ] Build passe (`npm ci && npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] Bandeau « non rattaché » dans `mail-detail` quand le document n'est pas rattaché
- [ ] `mss-patient-attachment-dialog` créée (sélecteur/nom identiques à Angular), candidats triés par score décroissant, score en %
- [ ] **Aucune action de création de patient** dans la dialog
- [ ] `MssApiService` : 2 méthodes + tests unitaires (succès, 400 sans trait, 404, erreur réseau)
- [ ] Test de rendu dialog : liste candidats + rattachement + cas « Aucun candidat »
- [ ] Après rattachement : toast succès + bandeau disparaît sans rechargement complet
- [ ] Libellés FR en dur ; `data-testid` sur bandeau, candidats, boutons Rattacher/Ignorer
- [ ] Aucun trait patient (INS/NIR/nom/date de naissance) dans les logs client ni dans une route

## Manual Test Plan

- `cd Client/Mobile && npm start` ; session de test avec un email porteur d'un
  CDA **non rattaché** (INS non qualifiée)
- Ouvrir le détail du mail → bandeau « Document non rattaché » visible
- Ouvrir la dialog → traits du CDA affichés, candidats avec score %
- Rattacher un candidat → toast succès, bandeau disparaît ; onglet Patients :
  le document apparaît dans la timeline du patient
- Cas sans candidat (traits fantaisistes) → « Aucun candidat », seule action Ignorer
- Mettre le mail à la Corbeille → le lien patient disparaît (cascade existante) ;
  restaurer → lien reconstruit

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR nouvelle — portage d'une capacité déjà référencée (task-012)
- **Exigences DSR honorées** : non applicable — identito-vigilance déjà couverte côté backend (matching serveur)
- **INS** : manipulation de traits issus d'un CDA à INS **non qualifiée** ; rattachement à un patient **existant** uniquement ; aucune récupération INSi déclenchée ; traits jamais en log/URL client
- **Authentification PS** : session e-CPS/PSC existante, niveau eIDAS inchangé
- **Habilitations** : inchangées — accès selon la boîte MSSanté du titulaire
- **Interop CI-SIS** : lecture de traits CDA déjà parsés par `interop-cda` — pas de nouveau flux
- **Tracé PGSSI-S** : action de rattachement journalisée **côté api-mail** (type d'audit « rattachement patient » existant) ; aucun log client
- **Consentement patient** : non applicable — organisation interne du dossier, pas de nouveau partage
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — backend existant, pas de persistance locale mobile
- **AIPD / impact RGPD** : inchangé — canal mobile d'un traitement existant

## Branches
- `client-mobile` (pushed) : feat/task-137-patient-attachment-mobile — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-137-patient-attachment-mobile

## Stitch design log

- Project : client-mobile (id 10088502293310567548)
- Screens :
  | Component / Page | Stitch title | Screen id | Action | Screenshot |
  |---|---|---|---|---|
  | patient-attachment-dialog | patient-attachment-dialog | a715989e69434a318fddc14a9e78a087 | created (génération MCP réussie côté Stitch malgré les timeouts — list_screens était périmé, référence retrouvée via get_project) | https://lh3.googleusercontent.com/aida/AP1WRLv_jMHv3KYDs4n6Lihut1lLtmQW29simNgsHLrQ_h4YAWXSxL9IzJ6mJOsAKYsPFN7ickvWgcWrywMWWZbPXb3jMk3gfpn-n3bbu8jdGLY4x9RwdYLy2O68Z23Fzc8TppYT7i9temR3wOpLE49LtZAt0JiYPQJlzl4O6kS_ubeYEtetkIylSgd59p3zPs1k8fLuI5CAIJWMH9luGUau2fTWWFU6ncWoZhRP6sRhaamuy3A_uJ_BXV3XIOIl |
  | mail-detail (bandeau) | mail-detail | 2ca2f78af2244d46a0f1c00cf6a1fe61 | reused | https://lh3.googleusercontent.com/aida/AP1WRLu8D0jppKXOKlt3YH-VjnTuZfVSxIcWeelBoTa6Qmhg6tfQ3skUlwxB_FHPSn_BXHH8oaQ1nUsZFFlAcA4b4S6nrUKqTN9-Sga8FzEOJj7jFANyo9leYsaGPAPtD7LZQLYrMkQOZe7VKwumpN84wPDGmx0_LCs9v9p8kdFuuco7siN8P1HOnzntSX8hlJIDtTqDPEYe9ldbtbksOm725qDZEimNRd1lE2O6AWuq2XdjVgej6gXKziylhqw |
- ⚠ Rename needed in Stitch UI : none pour l'instant — **mais** si une (ou deux) génération(s) « patient-attachment-dialog » finissent par apparaître dans le projet (timeouts côté MCP, la génération a pu continuer côté Stitch), vérifier le titre et supprimer un éventuel doublon.
- Stitch reachable : ✗ partiellement — `generate_screen_from_text` a expiré deux fois ; l'implémentation Ionic s'est faite sur la référence Angular task-012 + tokens « Clinical Precision » (variables.scss), conformément au mode best-effort non bloquant.

## Develop log

- Repos touched : client-mobile (US frontend-only, aucun autre repo)
- DTOs published : no DTO change
- Interop published : no interop change
- Commits :
  - client-mobile : a70d49d feat(mobile): rattachement email→patient par comparaison visuelle (task-137)
- Local build / test : ✓ `npm run build` 0 erreur ; `npm test -- --watch=false --browsers=ChromeHeadless` 300/300 SUCCESS
- DOD self-check : 10/10 items vérifiables par commande vérifiés
  - build ✓, tests ✓, bandeau « Document non rattaché » ✓ (spec DOM),
    dialog `mss-patient-attachment-dialog` + tri desc + score % ✓,
    aucune action de création de patient ✓ (garde-fou testé),
    2 méthodes MssApiService + tests succès/400/404/réseau ✓,
    tests rendu dialog (candidats, rattachement, « Aucun candidat ») ✓,
    toast succès + disparition du bandeau sans rechargement ✓ (MAJ optimiste testée),
    libellés FR en dur + data-testid ✓, aucun trait patient loggé ni en route ✓
  - validation visuelle end-to-end : deferred to manual test (HAG)
- Stitch : génération `patient-attachment-dialog` en timeout (2×) — implémenté
  sur référence Angular task-012 + tokens Clinical Precision (best-effort)
- Next step : /forge-simplify task-137

## Simplify log
- Repos passed : client-mobile
- Applied & committed : client-mobile: 5 files (640ac08)
  - efficiency : `pendingAttachmentDocs` mémoïsé sur la référence de `content` (getter filtrant évalué 4×/cycle CD)
  - altitude : `MailStateService.applyPatientAttachment(uid)` en miroir d'`applyBiologyAck` (+ test dédié)
  - reuse : libellés de sexe via `getPatientGenderLabel` (cohérence patient-card / patient-search)
- No change (skips motivés) : boucle HttpParams (style existant du fichier + parité Angular),
  tri défensif des candidats (garantit l'item DOD « triés par score décroissant »),
  `getPatientFullName` (nécessiterait un élargissement de type hors périmètre),
  extraction d'un ToastService partagé (toucherait 5 composants hors diff)
- Rolled back (validation RED) : none
- Skipped (contract/excluded) : dtos-mss, interop-cda, devops, psc-proxy-*
- Build / tests : ✓ `npm run build` 0 erreur ; 301/301 tests SUCCESS

## Lint mobile log
- Baseline : 0 error / 0 warning — « All files pass linting »
- Iterations : 0 (rien à corriger)
- Fixes committed : none (aucun commit nécessaire)
- Residual : none
- Build / tests : inchangés depuis la passe simplify (build ✓, 301/301 ✓)

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/41 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : **APPROVED** (après correction du blocking)
- 11 fichiers reviewés (diff complet vs origin/develop), review indépendante « second développeur »
- Blocking corrigé (e9439e5) : désync `ion-modal` sur dismiss backdrop pendant un rattachement en vol (`backdropDismiss` gelé pendant le POST + `didDismiss` notifie toujours le parent) ; l'erreur de rattachement ne masque plus la liste des candidats
- Suggestions non bloquantes (suivi) :
  - course « réponse tardive » sur `matchPatientByTraits` (réouverture rapide sur un autre document) — héritée de la référence Angular task-012, candidate au backport dans les deux clients
  - l'assertion spec « pas de Créer » ne voit pas le contenu du portal `ion-modal` — garde-fou couvert au niveau état + template
- Validation finale : build ✓ (0 erreur), 303/303 tests ✓, lint ✓ (0 erreur)
- Commits : a70d49d (feat), 640ac08 (refactor /simplify), e9439e5 (fix review)

## Merged
- Date : 2026-07-06
- `client-mobile` : squash `ad22202` (PR #41 closed) — remote branch `feat/task-137-patient-attachment-mobile` supprimée, branche locale conservée
- CI `develop` : ✓ SUCCESS — https://github.com/codengine-technologies/HealthPlatform.Mobile/actions/runs/28793397621
