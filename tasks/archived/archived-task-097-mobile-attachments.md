# todo-task-097-mobile-attachments.md — Pièces jointes (mail-attachment)

**Repos**: client-mobile
**Single frontend**: true
**Dependencies**: task-096
**Epic**: E012

## Objective

Afficher et exploiter les **pièces jointes** d'un email à parité avec
`client-angular` (`MailAttachmentComponent`) : liste fusionnée des pièces
jointes MIME **et** des pièces des documents médicaux, **téléchargement**,
**prévisualisation** lorsque possible, et **téléchargement de toutes les PJ en
ZIP**.

### Structure cible (miroir Angular)

```
Client/Mobile/src/app/features/mail/components/
└── mail-attachment/    # mss-mail-attachment (liste des PJ + actions)
```

Intégré dans `mss-mail-detail` (sous le corps du mail), comme en Angular.

### Parité (miroir MailAttachmentComponent)

- **Entrées** : `attachments: AttachmentDto[]` (MIME + médicales fusionnées et
  dédoublonnées, `mergedAttachments` côté detail), `folderPath`, `uid`,
  `selectedKey`
- **Sortie** : `attachmentSelected` (pour prévisualisation inline)
- Pour chaque PJ : nom, type, taille, icône selon le type
- **Télécharger** une PJ (`download`)
- **Prévisualiser** inline si le type est prévisualisable (PDF, image)
  (`select` → preview ; sinon download), adapté au mobile (ouverture
  plein écran / visionneuse)
- **Tout télécharger en ZIP** (`downloadAllAsZip`)

> Sur mobile (Capacitor) le téléchargement peut passer par le navigateur /
> l'API de fichiers ; l'important est la **parité fonctionnelle** (l'utilisateur
> récupère/visualise les mêmes PJ qu'en web).

### Périmètre API (mss-api.service)

Calqué sur Angular : `downloadAttachment(folderPath, uid, fileName)`,
`downloadAllAttachments(folderPath, uid)` (ZIP). Aucun nouvel endpoint backend.

> Rappel technique back (mémoire `reference_ziparchive_kestrel_sync_io`) : le
> ZIP est produit côté backend ; le mobile ne fait que consommer le flux. Aucun
> impact mobile, mais ne pas réimplémenter la génération ZIP côté client.

## Scénarios d'acceptation

1. **Lister les PJ** — Quand j'ouvre un email avec pièces jointes, alors je
   vois la liste fusionnée (MIME + documents médicaux) avec nom, type, taille.
2. **Télécharger une PJ** — Quand je tape « télécharger » sur une PJ, alors le
   fichier est récupéré.
3. **Prévisualiser** — Quand je tape sur une PJ prévisualisable (PDF/image),
   alors elle s'affiche en visionneuse ; sinon elle est téléchargée.
4. **Tout en ZIP** — Quand je tape « tout télécharger », alors un ZIP de toutes
   les PJ est récupéré.
5. **Parité** — Les PJ visibles sont les mêmes qu'en Angular pour le même email.

## Definition of Done

- [ ] Build passes (`npm run build`, 0 erreurs)
- [ ] Tests pass (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échecs)
- [ ] Composant `mss-mail-attachment` créé (standalone, nom miroir) et intégré dans `mss-mail-detail`
- [ ] Liste fusionnée MIME + documents médicaux (dédoublonnée), avec nom/type/taille/icône
- [ ] Téléchargement d'une PJ fonctionnel
- [ ] Prévisualisation inline pour PDF/image (sinon download)
- [ ] Téléchargement « tout en ZIP » fonctionnel
- [ ] Parité de la liste des PJ vérifiée vs Angular sur un email à PJ médicales + MIME
- [ ] Libellés FR en dur ; `data-testid` sur boutons (télécharger, prévisualiser, tout télécharger)
- [ ] Tests composant : `mss-mail-attachment` (rendu liste + émission `attachmentSelected` + action download mockée)
- [ ] Tests service : `mss-api.service` (downloadAttachment / downloadAllAttachments mockés)
- [ ] Aucun nom de fichier ni contenu de santé en clair dans les logs

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Lancer le mobile : `cd Client/Mobile && npm start`
- Se connecter en PSC, ouvrir un email **avec pièces jointes** (idéalement MIME + document médical avec PDF)
- **Vérifier** la liste des PJ (parité avec Angular : mêmes fichiers, types, tailles)
- Télécharger une PJ → fichier récupéré
- Prévisualiser un PDF / une image → visionneuse plein écran
- « Tout télécharger » → ZIP contenant toutes les PJ

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : MSSanté (récupération des pièces jointes des messages)
- **INS** : non manipulée directement (les PJ peuvent contenir des DSCP — voir HDS/sécurité)
- **Authentification PS** : PSC / e-CPS (en place)
- **Habilitations** : RPPS via claim PSC (back)
- **Interop CI-SIS** : les PJ médicales proviennent de documents CDA déjà traités côté `interop-cda` (back)
- **Tracé PGSSI-S** : téléchargement de pièce jointe journalisé côté backend — conservation 6 ans
- **Consentement patient** : non applicable (lecture boîte PS)
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — les PJ téléchargées (DSCP) ne sont pas mises en cache en clair de façon persistante ; respecter les bonnes pratiques de stockage temporaire Capacitor
- **AIPD / impact RGPD** : inchangé — réplication mobile d'une fonction déjà tracée

## Branches
- `client-mobile` (pushed) : feat/task-097-mobile-attachments — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-097-mobile-attachments

> Single frontend (client-mobile only). Dépend de task-096 (mergé @8764368).

## Develop log
- Repos : client-mobile
- mss-mail-attachment + preview inline dans mss-mail-detail + mss-api download/zip
- Build ✓ · Tests ✓ 39/39 (7 nouveaux) · Lint ✓
- Commit : client-mobile @a8c6c03

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/3 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : APPROVED · Build ✓ · Tests ✓ 39/39 · Lint ✓
- Liste fusionnée+dédupliquée, download/ZIP, preview image/pdf/texte ; blob URLs révoquées ; FR + data-testid

## Merged
- Merged : 2026-06-18 (squash) by human authorization
- client-mobile : develop @e59d54d (PR #3 closed)
- Local feature branch conservée
