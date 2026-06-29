# todo-task-098-mobile-biology-ack.md — Biologie : affichage + acquittement

**Repos**: client-mobile
**Single frontend**: true
**Dependencies**: task-096
**Epic**: E012

## Objective

Afficher les **résultats de biologie** d'un document médical (tableau des
valeurs flaggées, parité `BiologyComponent` d'Angular) **et** permettre au
médecin de les **acquitter** via les 5 actions standard (parité
`BiologyAckPanelComponent`), avec confirmation pour les **codes critiques**
(LL / HH / AA). Inclure le **badge d'acquittement** dans la ligne inbox et le
**chip de filtre** « acquittements en attente ».

### Structure cible (miroir Angular)

```
Client/Mobile/src/app/
├── core/models/biology-ack.model.ts            # BiologyAckDto, BiologyAckActionType,
│                                               #   BiologyAckResolutionState, BiologyAckRequestDto
└── features/mail/components/
    ├── biology/                    # affichage du tableau de biologie (dans mss-mail-body)
    ├── biology-ack-panel/          # mss-biology-ack-panel (5 actions + note)
    ├── biology-ack-confirm-dialog/ # mss-biology-ack-confirm-dialog (codes critiques)
    ├── biology-ack-badge/          # mss-biology-ack-badge (statut dans la ligne inbox)
    └── inbox-biology-ack-chip/     # mss-inbox-biology-ack-chip (filtre inbox)
```

### Parité

- **Affichage biologie** (dans `mss-mail-body`, onglet biologie si présent) :
  tableau des résultats `MailMedicalDocumentBiologyDto` (nom, valeur, unité,
  code d'interprétation L/H/A/N et critiques LL/HH/AA), **mise en évidence des
  valeurs flaggées** — read-only, parité visuelle Angular.
- **Acquittement** (`mss-biology-ack-panel`, sous le corps, pour chaque CDA à
  biologie flaggée) : 5 boutons d'action — **Viewed**, **InProgress**,
  **MarkResolved**, **MarkInvalid**, **ArchiveForLater** — + note optionnelle.
- **Codes critiques** (LL/HH/AA) → ouverture de
  `mss-biology-ack-confirm-dialog` avant envoi (parité
  `BiologyAckConfirmDialogComponent`).
- **Badge inbox** (`mss-biology-ack-badge`) dans `mss-mail-header` : statut
  Pending / InProgress / Resolved.
- **Chip filtre** (`mss-inbox-biology-ack-chip`) dans la barre de filtre inbox :
  n'afficher que les mails à acquittements en attente (émet l'ensemble d'UIDs).

### Périmètre API (mss-api.service)

`postBiologyAck(documentId, BiologyAckRequestDto)` (parité Angular →
`POST /api/v1/medical-documents/{id}/biology-ack`). Mise à jour de l'état via
`mail-state.service` (`applyBiologyAck(uid, ack)`). Aucun nouvel endpoint backend.

## Scénarios d'acceptation

1. **Voir la biologie** — Quand j'ouvre un email à document médical de biologie,
   alors je vois le tableau des résultats avec les valeurs flaggées mises en évidence.
2. **Acquitter** — Quand je choisis une action d'acquittement (ex. « Vu »),
   alors l'acquittement est enregistré et l'état du mail se met à jour.
3. **Code critique** — Quand je veux acquitter un résultat à code critique
   (LL/HH/AA), alors une confirmation m'est demandée avant l'enregistrement.
4. **Badge inbox** — La ligne inbox affiche le statut d'acquittement (en attente / en cours / résolu).
5. **Filtre** — Le chip « acquittements en attente » filtre la liste pour ne
   montrer que les mails concernés.

## Definition of Done

- [ ] Build passes (`npm run build`, 0 erreurs)
- [ ] Tests pass (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échecs)
- [ ] Composants `biology`, `mss-biology-ack-panel`, `mss-biology-ack-confirm-dialog`, `mss-biology-ack-badge`, `mss-inbox-biology-ack-chip` créés (noms miroir)
- [ ] Tableau de biologie affiché dans `mss-mail-body` avec valeurs flaggées mises en évidence (parité visuelle)
- [ ] 5 actions d'acquittement fonctionnelles + note optionnelle
- [ ] Confirmation obligatoire pour codes critiques LL/HH/AA avant `postBiologyAck`
- [ ] Badge d'acquittement dans `mss-mail-header` ; chip de filtre dans la liste
- [ ] État du mail mis à jour après acquittement (`applyBiologyAck`)
- [ ] Libellés FR en dur ; `data-testid` sur les 5 boutons d'action, la note, la confirmation, le chip
- [ ] Tests composant : `mss-biology-ack-panel` (déclenche `postBiologyAck`, confirmation sur code critique), `biology` (rendu tableau + flag), `mss-biology-ack-badge` (résolution du statut)
- [ ] Tests service : `mss-api.service.postBiologyAck` mocké ; `mail-state.applyBiologyAck`
- [ ] Aucune valeur de biologie / INS / identité patient en clair dans les logs

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Lancer le mobile : `cd Client/Mobile && npm start`
- Se connecter en PSC, ouvrir un email **à document médical de biologie avec valeurs flaggées**
- **Vérifier** le tableau de biologie (parité Angular : mêmes valeurs, unités, codes, mise en évidence)
- Acquitter avec « Vu » → l'état se met à jour ; vérifier le badge dans la liste
- Acquitter un résultat **critique** (LL/HH/AA) → la confirmation s'affiche
- Activer le chip « acquittements en attente » → la liste se restreint

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : biologie médicale (acquittement de CR de biologie LBM)
- **Vague Ségur** : V2
- **Exigences DSR honorées** : MSSanté + traitement des CR de biologie (volet CR-BIO CI-SIS)
- **INS** : identité patient du document affichée au PS — jamais en clair dans logs/URL
- **Authentification PS** : PSC / e-CPS — l'acquittement est une action médecin tracée (eIDAS substantiel)
- **Habilitations** : RPPS via claim PSC ; l'acquittement est imputé au PS authentifié
- **Interop CI-SIS** : résultats de biologie issus du CDA r2 (CR-BIO) déjà parsé côté `interop-cda` ; codes **LOINC** + interprétation HL7 (L/H/A/LL/HH/AA) affichés tels quels (pas de re-codage côté mobile)
- **Tracé PGSSI-S** : chaque acquittement (action, auteur, horodatage, note) journalisé côté backend — imputabilité, conservation 6 ans
- **Consentement patient** : non applicable
- **Référentiels métier** : LOINC (codes d'analyse), interprétation HL7 (abnormal flags)
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé — réplication mobile d'une action déjà tracée côté Angular/back

## Branches
- `client-mobile` (pushed) : feat/task-098-mobile-biology-ack — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-098-mobile-biology-ack

> Single frontend (client-mobile only). Dépend de task-096 (mergé @e59d54d via 097).

## Develop log
- Repos : client-mobile
- mss-biology, mss-biology-ack-panel, mss-biology-ack-confirm-dialog, mss-biology-ack-badge, mss-inbox-biology-ack-chip
- Intégration mail-body (onglet bio + panneaux), mail-header (badge), inbox (chip) ; mail-state (filter + applyBiologyAck) ; mss-api (recordBiologyAck + pending-mail-uids)
- Build ✓ · Tests ✓ 56/56 (17 nouveaux) · Lint ✓
- Commit : client-mobile @ac8cc9b

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/4 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : APPROVED · Build ✓ · Tests ✓ 56/56 · Lint ✓
- Workflow acquittement + friction confirmation (critiques LL/HH/AA) ; tableau bio flaggée ; FR + data-testid ; aucune donnée santé en clair

## Merged
- Merged : 2026-06-18 (squash) by human authorization
- client-mobile : develop @c94fa90 (PR #4 closed)
- Local feature branch conservée
