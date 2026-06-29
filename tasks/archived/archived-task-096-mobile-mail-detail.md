# todo-task-096-mobile-mail-detail.md — Parité consultation email (mail-detail + mail-body)

**Repos**: client-mobile
**Single frontend**: true
**Dependencies**: task-095
**Epic**: E012

## Objective

Livrer la **consultation d'un email à parité de contenu** avec
`client-angular`. À l'ouverture d'un email, le médecin doit voir **exactement
les mêmes informations** que sur le web : titre (titre du document médical),
bloc identité patient, badges/alertes, destinataires, corps HTML (avec
bascule texte brut), et les **documents médicaux structurés**.

Refactore la page `mail-detail.page` (qui fait tout actuellement) en
composants miroir d'Angular (`features/mail/components/mail-detail`,
`mail-body`, `medical-html-frame`).

### Structure cible (miroir Angular)

```
Client/Mobile/src/app/features/mail/components/
├── mail-detail/        # mss-mail-detail (orchestrateur du visualiseur)
├── mail-body/          # mss-mail-body (onglets : corps mail / docs médicaux)
└── medical-html-frame/ # mss-medical-html-frame (rendu HTML CDA sandboxé)
```

`mail-detail.page` devient un hôte mince projetant `mss-mail-detail`.

### Parité d'affichage (miroir MailDetailComponent + MailBodyComponent)

- **En-tête** : sujet d'affichage = titre du document médical s'il existe,
  sinon objet (`displaySubject`) ; expéditeur (`senderName`) ; **bloc identité
  patient** (nom + INS, `patientIdentityDisplay`) ; date ; **badge de version
  de document** (v2, v3…) si applicable
- **Bloc destinataires** : To et Cc (`recipients`, `ccRecipients`)
- **Bloc badges/alertes** : compteur PJ, compteur documents médicaux, badge
  intégration patient en attente, badge document remplacé/dupliqué (lecture
  seule — les workflows de décision sont hors scope), badge biologie
- **Corps multi-onglets** (`mss-mail-body`) :
  - Onglet 0 : corps du mail (HTML assaini OU texte brut, bascule
    `togglePlainText`) ; **bannière de contenu distant bloqué** + bouton
    « Afficher les images » (parité `showRemoteImages`)
  - Onglets 1..N : un par document médical (CDA) — rendu **structuré** via
    `mss-medical-html-frame` ; mode PDF si PDF externe présent
- **Assainissement HTML** : le corps et le HTML médical sont rendus de façon
  sûre (sanitization), aucune exécution de script

> Hors scope ici : pièces jointes téléchargeables (task-097), tableau biologie
> + acquittement (task-098), actions lu/flag/suppression (task-099), répondre/
> transférer (task-100). Les badges associés peuvent s'afficher mais sans action.

### Périmètre API (mss-api.service)

`getEmailContent(folderPath, uid)` (déjà présent) renvoie `MailContentDto`
(bodyHtml, body, medicalDocuments[]). Étendre `MailContentDto` /
`MailMedicalDocumentDto` côté modèles pour porter les documents médicaux
structurés (titre, date, catégorie, HTML structuré, indicateurs PDF/biologie),
calqués sur Angular. Aucun nouvel endpoint backend.

## Scénarios d'acceptation

1. **Ouvrir un email** — Quand j'ouvre un email, alors je vois l'en-tête
   (titre/doc médical, expéditeur, identité patient, date, badges) identique à Angular.
2. **Corps HTML** — Le corps HTML s'affiche assaini ; les images distantes
   sont bloquées par défaut avec un bouton pour les révéler.
3. **Bascule texte brut** — Je peux basculer entre HTML et texte brut.
4. **Documents médicaux** — S'il y a un ou plusieurs documents médicaux, je
   les vois en onglets, rendus en HTML structuré (parité Angular).
5. **Destinataires** — Je vois les destinataires To et Cc.

## Definition of Done

- [ ] Build passes (`npm run build`, 0 erreurs)
- [ ] Tests pass (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échecs)
- [ ] Composants `mss-mail-detail`, `mss-mail-body`, `mss-medical-html-frame` créés (standalone, noms miroir)
- [ ] `mail-detail.page` refactorée en hôte mince
- [ ] En-tête à parité : titre (doc médical), expéditeur, **identité patient**, date, badges PJ/doc médical/version
- [ ] Bloc destinataires To + Cc affiché
- [ ] Corps HTML **assaini** + bascule texte brut + blocage images distantes (avec révélation)
- [ ] Documents médicaux rendus en onglets via `mss-medical-html-frame`
- [ ] Comparaison visuelle OK avec Angular sur un email à document médical
- [ ] Libellés FR en dur ; `data-testid` sur boutons (bascule texte brut, afficher images, onglets)
- [ ] Tests composant : `mss-mail-detail` (en-tête + identité patient rendus), `mss-mail-body` (onglets + bascule HTML/texte), `mss-medical-html-frame` (rendu HTML assaini sans script)
- [ ] Aucune donnée de santé en clair dans les logs (INS, contenu CDA, identité patient)
- [ ] Aucun script exécuté depuis le HTML du mail / du CDA (XSS bloqué)

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Lancer le mobile : `cd Client/Mobile && npm start`
- Se connecter en PSC, ouvrir un répertoire, ouvrir un email **avec document médical**
- **Vérifier** côte à côte avec `client-angular` : en-tête identique (titre du
  doc médical, identité patient + INS, date, badges), corps HTML identique,
  documents médicaux en onglets, rendu structuré identique
- Basculer en texte brut puis revenir en HTML
- Ouvrir un email avec images distantes → vérifier le blocage puis la révélation
- Ouvrir un email simple (sans doc médical) → l'objet est utilisé comme titre

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : MSSanté (consultation des contenus), affichage VSM/CR-BIO/CR-IMG (volets CI-SIS) en lecture
- **INS** : identité patient (INS) affichée au PS — jamais en clair dans logs/URL
- **Authentification PS** : PSC / e-CPS (en place)
- **Habilitations** : RPPS via claim PSC (back)
- **Interop CI-SIS** : documents CDA r2 (volets ANS) déjà parsés côté `interop-cda` ; le mobile **n'effectue aucun parsing CDA** — il affiche le HTML structuré fourni par le backend
- **Tracé PGSSI-S** : consultation du contenu d'un email / document médical journalisée côté backend — conservation 6 ans
- **Consentement patient** : non applicable (lecture boîte PS)
- **Référentiels métier** : LOINC/CIM-10 portés par le CDA (affichage, pas de validation côté mobile)
- **Hébergement HDS** : oui — pas de persistance locale de DSCP hors session
- **AIPD / impact RGPD** : inchangé — réplication mobile d'un affichage déjà tracé

## Branches
- `client-mobile` (pushed) : feat/task-096-mobile-mail-detail — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-096-mobile-mail-detail

> Single frontend (`client-mobile` only). Dépend de task-095 (mergé sur develop @f456a09). Pas de dtos-mss.

## Develop log
- Repos touched : client-mobile
- Composants : mss-mail-detail, mss-mail-body, mss-medical-html-frame + core/utils/remote-content
- mail-detail.page → hôte mince ; toggle texte brut en toolbar
- Build ✓ · Tests ✓ 32/32 (12 nouveaux) · Lint ✓ clean
- Rendu sûr : innerHTML assaini (mail) + iframe sandbox blob (CDA) ; images distantes bloquées
- Commit : client-mobile @dec408a

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/2 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : APPROVED · Build ✓ · Tests ✓ 32/32 · Lint ✓
- Parité en-tête + corps ; XSS bloqué (sanitization + iframe sandbox) ; FR en dur ; data-testid

## Merged
- Merged : 2026-06-18 (squash) by human authorization
- client-mobile : develop @8764368 (PR #2 closed)
- Inclut le fix auto-hauteur iframe (medical-html-frame)
- Local feature branch conservée
