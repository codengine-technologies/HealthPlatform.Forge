# todo-task-100-mobile-compose-send.md — Compose / envoi (mail-compose + html-editor)

**Repos**: client-mobile
**Single frontend**: true
**Dependencies**: task-096
**Epic**: E012

## Objective

Permettre au médecin d'**envoyer un email MSSanté** depuis le client mobile, à
parité fonctionnelle avec le compose d'Angular pour le périmètre retenu :
**Nouveau message**, **Répondre**, **Transférer**, champs **To / Cc / Cci**,
**objet**, **corps HTML**, **pièces jointes**, **demande d'accusé de lecture**.

### Structure cible (miroir Angular)

```
Client/Mobile/src/app/
├── core/models/draft.model.ts                  # SaveDraftDto, SendMailResultDto (exploités ici)
└── features/mail/components/
    ├── mail-compose/   # mss-mail-compose (modal de rédaction : new/reply/forward)
    └── html-editor/    # mss-html-editor (éditeur de corps HTML — version mobile)
```

Ouverture du compose via `mail-event.service` (`openCompose$`), parité Angular.

### Parité (périmètre retenu)

- **Modes** : Nouveau, **Répondre** (pré-remplit To + objet « Re: » + cite le
  message + threading In-Reply-To/References), **Transférer** (pré-remplit
  objet « Fwd: » + corps cité + reprend les PJ).
- **Destinataires** : champs **To / Cc / Cci** (affichage Cc/Cci repliable),
  ajout/suppression d'adresses.
- **Objet** et **corps HTML** (`mss-html-editor` — éditeur léger : gras,
  italique, listes, liens ; pas besoin de l'éditeur riche complet d'Angular).
- **Pièces jointes** : upload de fichiers (Capacitor / input file), liste,
  suppression avant envoi.
- **Accusé de lecture** : case « demander un accusé de lecture »
  (`requestReadReceipt`).
- **Envoi** : `send()` → `sendMail(dto)` ; à succès, fermeture + retour liste,
  message de confirmation ; à l'échec, message d'erreur `ProblemDetails`.

> **Hors scope** (par décision PO) : signatures, templates, éditeur HTML riche
> complet, suggestions de contacts/autocomplete, brouillons auto-sauvegardés,
> cancel-and-replace, bloc « réponse patient ». À noter dans le corps.

### Périmètre API (mss-api.service — parité Angular)

`sendMail(SendMailDto)` → `POST /api/v1/mail/send` (renvoie `SendMailResultDto`).
Upload de PJ selon le contrat existant consommé par Angular. Aucun nouvel
endpoint backend.

## Scénarios d'acceptation

1. **Nouveau message** — Quand je rédige un nouveau message (To, objet, corps)
   et que je l'envoie, alors il part et je reçois une confirmation.
2. **Répondre** — Depuis un email ouvert, « Répondre » pré-remplit le
   destinataire, l'objet « Re: » et cite le message ; l'envoi conserve le
   threading (conversation côté serveur).
3. **Transférer** — « Transférer » pré-remplit l'objet « Fwd: », cite le corps
   et reprend les pièces jointes.
4. **Cc / Cci** — Je peux ajouter des destinataires en Cc et Cci.
5. **Pièces jointes** — Je peux joindre un ou plusieurs fichiers et en retirer
   avant l'envoi.
6. **Accusé de lecture** — Je peux demander un accusé de lecture.
7. **Erreur** — Si l'envoi échoue, un message d'erreur clair (ProblemDetails)
   s'affiche et le brouillon en cours n'est pas perdu (reste dans le modal).

## Definition of Done

- [ ] Build passes (`npm run build`, 0 erreurs)
- [ ] Tests pass (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échecs)
- [ ] Composants `mss-mail-compose` et `mss-html-editor` créés (noms miroir, standalone)
- [ ] Modes Nouveau / Répondre / Transférer fonctionnels (pré-remplissage + threading pour Répondre)
- [ ] Champs To / Cc / Cci (Cc/Cci repliables) avec ajout/suppression d'adresses
- [ ] Objet + corps HTML éditables
- [ ] Pièces jointes : upload, liste, suppression avant envoi
- [ ] Case « demander un accusé de lecture »
- [ ] Envoi via `sendMail` ; confirmation au succès ; erreur `ProblemDetails` à l'échec (brouillon conservé dans le modal)
- [ ] Libellés FR en dur ; `data-testid` sur champs et boutons (envoyer, ajouter PJ, Cc, Cci, accusé)
- [ ] Tests composant : `mss-mail-compose` (Répondre pré-remplit + envoi déclenche `sendMail` ; gestion d'erreur), `mss-html-editor` (édition basique)
- [ ] Tests service : `mss-api.sendMail` mocké (succès + échec)
- [ ] Aucun RPPS dans l'objet / les en-têtes ; aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Lancer le mobile : `cd Client/Mobile && npm start`
- Se connecter en PSC
- **Nouveau message** : saisir un destinataire MSSanté de test, un objet, un corps, joindre un fichier, demander un accusé, envoyer → confirmation ; vérifier l'arrivée dans « Envoyés »
- **Répondre** : ouvrir un email reçu, « Répondre » → To + objet « Re: » pré-remplis, corps cité ; envoyer
- **Transférer** : « Transférer » → objet « Fwd: », corps cité, PJ reprises ; envoyer
- Ajouter un destinataire en Cc puis en Cci
- Provoquer une erreur (adresse invalide) → message d'erreur clair, brouillon conservé
- Comparer le comportement avec `client-angular`

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : MSSanté (émission de messages depuis une boîte PS)
- **INS** : si réponse à un mail patient, l'INS éventuelle reste côté backend — jamais en clair dans l'objet/les en-têtes
- **Authentification PS** : **PSC / e-CPS exigé** — l'envoi MSSanté est une action sensible (signature/émission), pas un simple mot de passe (niveau eIDAS substantiel)
- **Habilitations** : RPPS via claim PSC ; l'émission est imputée à l'adresse MSSanté du PS authentifié
- **MSSanté** : adresse émettrice = boîte du PS connecté ; certificat IGC Santé géré côté backend ; **jamais de RPPS dans l'objet ou les en-têtes** (l'adresse seule identifie l'émetteur)
- **Interop CI-SIS** : non applicable pour un message simple ; un éventuel document joint relève du transport MSSanté
- **Tracé PGSSI-S** : envoi (succès / échec), demande d'accusé de lecture journalisés côté backend — imputabilité, conservation 6 ans
- **Consentement patient** : non applicable (échange entre PS)
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — les pièces jointes en cours de rédaction (DSCP) ne sont pas persistées en clair hors session
- **AIPD / impact RGPD** : inchangé — réplication mobile d'une fonction d'émission déjà tracée côté Angular/back

## Branches
- `client-mobile` (pushed) : feat/task-100-mobile-compose-send — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-100-mobile-compose-send

> Single frontend (client-mobile only). Dépend de task-096 (mergé @5086a82).

## Develop log
- Repos : client-mobile
- mss-mail-compose (modal global) + mss-html-editor ; new (FAB inbox) / reply / forward (mss-mail-detail) ; openCompose$ typé
- mss-api.sendMail (OutgoingMailDto → /api/v1/mail/sendmail)
- Build ✓ · Tests ✓ 70/70 (7 nouveaux) · Lint ✓
- Commit : client-mobile @53e0687

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/6 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : APPROVED · Build ✓ · Tests ✓ 70/70 · Lint ✓
- new/reply/forward + To/Cc/Cci + PJ + accusé ; threading ; ProblemDetails ; PSC ; pas de RPPS en objet ; FR + data-testid

## Merged
- Merged : 2026-06-18 (squash) by human authorization
- client-mobile : develop @17bfd29 (PR #6 closed)
- Inclut le fix OutgoingMailDto (uid + folderPath pour le contrat sendmail)
- Local feature branch conservée
