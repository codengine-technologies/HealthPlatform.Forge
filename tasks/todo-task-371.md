# todo-task-371.md — Le mail affiché est toujours celui qui est sélectionné : contenu, documents médicaux, biologie et synthèse IA

**Repos**: client-angular, client-mobile, api-mail (catalogue e2e `Api/Mail/e2e/scenarios.yml` seulement)
**Dependencies**: — (aucune). task-372 (import Weda) et task-373 (dossier patient) en dépendent pour leur part d'identito-vigilance.
**Epic**: E009
**Single frontend**: false — weda2 et le mobile (décision humaine du 2026-10-13).
**Priorité**: **1** — le contenu, les documents CDA, les résultats de biologie et le panneau d'acquittement d'un mail s'affichent sous l'en-tête d'un autre : un résultat critique peut être acquitté, un document importé ou un compte rendu lu pour le mauvais patient.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-08 ✔, ANG-21, ANG-40, ANG-41, ANG-55, ANG-73**).

## Ce qui est établi

- **ANG-08** — `mail-detail.component.ts:737-750, 777-806` : chaque sélection lance un `getEmailContent` indépendant, sans annulation ; `mailContent` n'est pas vidé au changement de mail. Pendant chaque chargement — et durablement si A répond après B ou si B échoue — le corps, les onglets CDA, la biologie, les pièces jointes, le panneau d'acquittement et la section Patient de B montrent le contenu de A (`mail-detail.component.html:705-740, 922-928`). Le garde `originalLoaded` (task-350) ne protège que Répondre et Transférer.
- **ANG-21** — `mail-summary.component.ts:48-52, 126-147` : la synthèse IA de A (génération lente) remplace celle de B sous l'identité patient de B ; `showSummary` n'est pas remis à faux au changement.
- **ANG-40** — l'identité d'un mail est réduite à son UID (`lastLoadedUid`, `updateMailInList`) alors que les UID repartent à 1 dans chaque dossier : dans la vue « Mails du patient », Archives/42 après INBOX/42 garde le contenu d'INBOX/42.
- **ANG-41 / ANG-55** — la vue en lecture seule (doublons, widget patient) et la fenêtre du document patient appliquent des réponses non annulées : le médecin supprime le mauvais exemplaire, ou lit le PDF d'un document sous le titre d'un autre.
- **ANG-73** — `mail-body.component.ts:61-74` remet l'onglet et « Afficher les images » à zéro à chaque changement d'entrée, pas seulement au changement de mail.

## Objective

Qu'un mail, ses documents médicaux, ses résultats et sa synthèse ne s'affichent **que** sous son propre en-tête : jamais de contenu, de document ou de synthèse d'un autre mail, même pendant un chargement, après un échec, ou quand les réponses arrivent dans le désordre.

### Périmètre

1. **Identité `(folderPath, uid)`** partout où un mail est désigné : chargement, cache local, mises à jour de la liste, synthèse, accusés.
2. **Chargement du contenu** annulable (`switchMap` sur `(folderPath, uid)`) ; contenu vidé à chaque changement de mail ; corps, onglets CDA, panneau latéral et section Patient rendus **seulement** quand le contenu chargé appartient au mail affiché.
3. **Synthèse IA** : requête annulée au changement de mail, réponse ignorée si elle ne correspond plus ; `showSummary` remis à faux.
4. **Vue en lecture seule** et **fenêtre du document** : annulation et garde de clé sur chaque chargement (contenu, PDF).
5. **`mail-body`** : réinitialisation de l'onglet et des images seulement au changement de `(folderPath, uid)`.

## Definition of Done

- [ ] Build et tests weda2 verts
- [ ] Tests unitaires et de composant rouges d'abord :
  - [ ] sélection de A puis de B, réponse de A arrivée en dernier : le contenu affiché est celui de B
  - [ ] pendant le chargement de B, ni le corps, ni les documents médicaux, ni le panneau d'acquittement, ni la section Patient de A ne sont rendus
  - [ ] chargement de B en échec : aucun contenu de A ne reste affiché
  - [ ] INBOX/42 puis Archives/42 : le contenu est rechargé
  - [ ] synthèse de A lente, B rapide : la synthèse affichée est celle de B
  - [ ] vue en lecture seule et fenêtre du document : une réponse d'un élément quitté est ignorée
  - [ ] un enrichissement SSE du même mail ne remet pas l'onglet ni « Afficher les images » à zéro
- [ ] Scénario E2E-DETAIL-005 « Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent » ajouté au catalogue (angular `requis` ; mobile : à trancher au `/start`, voir l'arbitrage), implémenté dans weda2 avec une latence injectée sur le premier mail
- [ ] Trou du filet : scénario prouvé rouge sur le code d'avant, ligne ajoutée dans `conventions/e2e.md`
- [ ] Aucune donnée de santé ajoutée aux journaux

> **⚠️ Arbitrage humain requis — le client mobile.** Le mobile n'a pas été audité ; son écran de lecture
> a pu reproduire le même chargement non annulé. Inclure `client-mobile` (scénario `requis` des deux
> côtés), ou déclarer une divergence temporaire avec une task mobile de vérification ?
>
> **Décision humaine (2026-10-13, avant `/forge 368 to 381`) : inclure le mobile.** `/develop` audite le
> même périmètre sur `client-mobile` et y corrige les défauts trouvés ; les scénarios e2e de la task sont
> `requis` sur angular **et** mobile.

## Manual Test Plan

1. Mail A portant un CDA lourd, mail B sans document : cliquer sur A puis aussitôt sur B → seuls le contenu et les documents de B s'affichent, à aucun moment ceux de A.
2. Couper le réseau, cliquer sur B → message d'échec, aucun contenu de A visible.
3. Ouvrir la synthèse IA sur A, passer aussitôt à B → la synthèse affichée est celle de B.
4. Vue « Mails du patient » : ouvrir deux mails de même numéro dans deux dossiers → chacun affiche son propre contenu.
5. Dialogue « Nettoyer les doublons » : passer vite d'un exemplaire à l'autre → l'aperçu suit toujours l'exemplaire sélectionné.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif
- **Exigences DSR honorées** : non applicable — rétablit l'identito-vigilance de l'affichage (un document est présenté avec le patient auquel il appartient)
- **INS** : non applicable en écriture ; la task garantit que l'identité affichée est celle du document affiché
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : CDA r2 — affichage seulement, aucun changement de format
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — DSCP affichées, aucune nouvelle donnée stockée
- **AIPD / impact RGPD** : inchangé
