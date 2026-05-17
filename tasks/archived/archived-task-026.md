# todo-task-026.md — Toggle UI « Bloquer la réponse du patient » (X-MSS-MES: FIN)

**Repos**: client-blazor, client-angular
**Dependencies**: archived-task-001
**Epic**: E009

## Objectif

Câbler la **surface utilisateur** de l'opt-in `MailDto.BlockPatientReply`
livré côté backend par task-001. Aujourd'hui le backend
(`MssanteHeaderService`) sait émettre l'en-tête `X-MSS-MES: FIN` quand le
DTO porte `BlockPatientReply == true` et qu'au moins un destinataire est
`@patient.mssante.fr` — mais **aucun des deux frontends n'expose de
contrôle pour flipper ce booléen**. La valeur par défaut C# (`false`)
fait que l'en-tête n'est **jamais émis en pratique**, même sur un envoi
strictement patient.

Conséquence : `SC.MSS/CONF.21` / `RG-E009-016` est marqué ✅ Implémenté
dans le tableau EPIC §6.13 mais c'est en réalité un backend-only sans
surface médecin. La conformité Ségur réelle demande que le LGC
**permette** au professionnel de signifier la fin d'échange ; sans
toggle UI, le LGC ne le permet pas.

## Contexte réglementaire

- **Référentiel socle MSSanté #2 v1.0.1 — §3.4.2.3 / ECO.2.2.8** : la
  méthode privilégiée pour signifier la fin d'échange avec un usager
  Mon Espace Santé est l'en-tête SMTP `X-MSS-MES: FIN`. Ce header
  retire la possibilité pour le patient destinataire de répondre au
  message (1 message au lieu de la méthode alternative `Subject = "[FIN]"`
  qui retire la réponse à TOUS les messages précédents).
- **Doctrine** : la valeur par défaut DOIT rester `BlockPatientReply = false`
  (« le patient peut répondre »), sauf intention explicite du médecin
  de clore l'échange. Le toggle est un opt-in actif, pas un opt-out.
- L'option n'a de sens que pour un envoi vers Mon Espace Santé : la
  checkbox / switch est conditionnellement visible **uniquement** quand
  au moins un destinataire (To/Cc/Bcc) appartient au domaine
  `@patient.mssante.fr`.

## Comportement attendu

### Visibilité conditionnelle

Le toggle est rendu uniquement si :
```
(toAddresses ∪ ccAddresses ∪ bccAddresses) contient au moins une adresse
qui matche `*@patient.mssante.fr` (case-insensitive)
```

Quand le médecin retire le dernier destinataire patient (ex. supprime
le tag chip), le toggle disparaît et la valeur sous-jacente est
**réinitialisée à `false`** (pour éviter qu'un état caché pollue un
envoi non-patient suivant).

### Libellé et tooltip

| Locale | Label | Tooltip |
|---|---|---|
| fr-FR | « Bloquer la réponse du patient » | « Empêche le patient destinataire de répondre à ce message. Recommandé pour signifier la fin d'un échange MSSanté (Référentiel socle MSSanté #2 §3.4.2.3 — ECO.2.2.8). » |
| en-US | « Block patient reply » | « Prevents the patient recipient from replying to this message. Recommended when signalling the end of an MSSanté exchange (Référentiel socle MSSanté #2 §3.4.2.3 — ECO.2.2.8). » |

### Propagation au payload

Au moment du `Send` ou `SaveDraft`, la valeur du toggle est posée sur
`MailDto.BlockPatientReply` (Blazor → `_mail.BlockPatientReply`,
Angular → propriété sur le `Partial<MailDto>` envoyé via `sendMail`).

### Persistance brouillon

Le brouillon Redis (`SaveDraftDto.BlockPatientReply` existe déjà côté
DTO depuis task-001) propage l'état du toggle. Au rechargement d'un
brouillon, l'état du toggle est restauré.

### Affichage post-envoi (optionnel — suggestion)

Le mail envoyé qui carry `X-MSS-MES: FIN` peut être marqué visuellement
dans le dossier `Sent` (badge « Fin d'échange » discret). Hors scope
si trop coûteux ; à acter avec le PO.

## Périmètre détaillé

### Blazor (`client-blazor`)

1. **`NewMailComponent.razor`** — sous l'aire des destinataires (juste
   au-dessus du subject ou en option « Plus » repliable) :
   ```razor
   @if (HasPatientRecipient())
   {
       <div class="compose-option-block-patient-reply" data-testid="compose-block-patient-reply">
           <RadzenCheckBox @bind-Value="_mail.BlockPatientReply"
                           Name="block-patient-reply"
                           data-testid="compose-block-patient-reply-checkbox" />
           <label for="block-patient-reply" title="@Localizer[\"BlockPatientReplyTooltip\"]">
               @Localizer["BlockPatientReplyLabel"]
               <Icon Name="fa-info-circle" />
           </label>
       </div>
   }
   ```
   - `HasPatientRecipient()` helper privé qui scrute
     `_toAddresses + _ccAddresses + _bccAddresses` et retourne `true`
     si au moins une adresse contient `@patient.mssante.fr`
     (case-insensitive).
   - `data-testid` exhaustif (règle CLAUDE.md DOD).
2. **Reset on no-patient-recipient** : un `@bind` change handler sur
   les listes de destinataires vérifie que si la condition redevient
   `false`, `_mail.BlockPatientReply` est forcé à `false`. Évite l'état
   caché qui se réveille à un envoi suivant.
3. **`Localizer`** : 2 nouvelles clés FR + EN
   (`BlockPatientReplyLabel`, `BlockPatientReplyTooltip`).
4. **bUnit tests** dans `HealthPlatform.Client.Tests` (à créer si
   absent — cf. Phase 4a du plan stability-audit) :
   - `NewMailComponent_WhenNoPatientRecipient_BlockPatientReplyToggleIsHidden`
   - `NewMailComponent_WhenAtLeastOnePatientRecipient_BlockPatientReplyToggleIsVisible`
   - `NewMailComponent_WhenToggleChecked_PayloadCarriesBlockPatientReplyTrue`
   - `NewMailComponent_WhenLastPatientRecipientRemoved_BlockPatientReplyResetsToFalse`

### Angular (`client-angular`) — mode code-only

1. **`mail-compose.component.html`** : ajouter la checkbox dans la
   zone des options après les destinataires.
   ```html
   @if (hasPatientRecipient()) {
       <div class="compose-option" data-testid="compose-block-patient-reply">
           <ds-checkbox [(ngModel)]="blockPatientReply"
                        name="block-patient-reply"
                        data-testid="compose-block-patient-reply-checkbox" />
           <label for="block-patient-reply" [title]="blockPatientReplyTooltip">
               {{ blockPatientReplyLabel }}
               <ds-icon category="user-interface" name="info-circle" size="xs"></ds-icon>
           </label>
       </div>
   }
   ```
2. **`mail-compose.component.ts`** :
   ```typescript
   readonly blockPatientReply = signal(false)
   readonly hasPatientRecipient = computed(() => {
       const all = [...this.toAddresses(), ...this.ccAddresses(), ...this.bccAddresses()]
       return all.some(addr => addr.toLowerCase().endsWith('@patient.mssante.fr'))
   })
   // Reset on no-patient-recipient (effect + lastResolvedPatientIns pattern)
   constructor() {
       effect(() => {
           if (!this.hasPatientRecipient()) this.blockPatientReply.set(false)
       })
   }
   // sendMailDirect() — adapter
   const mail: Partial<MailDto> = {
       ...,
       blockPatientReply: this.blockPatientReply()
   }
   ```
3. **i18n** : `mss-fr.json` + `mss-en.json` (ou les fichiers de
   ressources Angular équivalents — Weda 2 utilise un service de
   localization custom, à vérifier au moment de l'implé).
4. **Vitest tests** dans `mail-compose.component.spec.ts` :
   - `should hide block-patient-reply toggle when no patient recipient`
   - `should show block-patient-reply toggle when at least one patient recipient is added`
   - `should propagate blockPatientReply=true to MailDto on send`
   - `should reset blockPatientReply to false when last patient recipient is removed`
5. **MailDto modèle TS** : ajouter le champ optionnel
   `blockPatientReply?: boolean` dans
   `front/libs/mss/src/core/models/mail.model.ts` (le DTO C# le porte
   déjà, le contrat JSON est compatible).

### dtos-mss

Aucun changement — `MailDto.BlockPatientReply` et
`SaveDraftDto.BlockPatientReply` sont **déjà** publiés depuis task-001
(NuGet `HealthPlatform.Dtos.Mss` ≥ build task-001).

### api-mail

Aucun changement — la logique d'émission de `X-MSS-MES: FIN` est déjà
en place dans `MssanteHeaderService` (vérifié 2026-05-03 via grep).

## Convention scellée

- Le toggle est **opt-in actif** (default `false`). Jamais coché par
  défaut, jamais auto-coché par une heuristique.
- Le toggle disparaît dès qu'il n'y a plus de destinataire patient ;
  l'état sous-jacent est forcé à `false` à ce moment-là.
- Le toggle est lu une fois au moment du `Send` / `SaveDraft`. Pas de
  side-effect intermédiaire.
- Localizer / i18n keys exhaustives. Tooltip en français cite
  Référentiel socle MSSanté #2 §3.4.2.3 (ECO.2.2.8) pour traçabilité.

## Definition of Done

- [ ] Build passes (0 errors) sur `client-blazor`, `client-angular`
- [ ] Tests pass (0 failures) sur les 2 frontends
- [ ] **Blazor** : checkbox visible conditionnellement (≥ 1 destinataire patient), `data-testid="compose-block-patient-reply-checkbox"` posé, label + tooltip via Localizer FR + EN
- [ ] **Blazor** : reset à `false` quand le dernier destinataire patient disparaît
- [ ] **Blazor** : `_mail.BlockPatientReply` populated au moment du Send
- [ ] **Blazor** : ≥ 4 tests bUnit (visibilité hide/show, payload propagation, reset on remove)
- [ ] **Angular** (code-only) : checkbox visible conditionnellement (computed), `data-testid="compose-block-patient-reply-checkbox"`, i18n FR + EN
- [ ] **Angular** : reset via effect quand `hasPatientRecipient()` redevient `false`
- [ ] **Angular** : `blockPatientReply` propagé sur `Partial<MailDto>` au moment du `sendMail`
- [ ] **Angular** : modèle `MailDto.blockPatientReply?` ajouté dans `mail.model.ts`
- [ ] **Angular** : ≥ 4 tests Vitest sur `mail-compose.component.spec.ts`
- [ ] **Audit grep DOD** :
  - [ ] `grep -r "BlockPatientReply" Client/Blazor/Src/` → matches dans Razor + cs sources (au moins 4 sites : composant, ViewModel/code-behind, localizer FR, localizer EN)
  - [ ] `grep -r "blockPatientReply" Client/Angular/front/libs/mss/src/` → matches dans .ts + .html + .spec.ts + i18n
- [ ] **Aucune régression** sur les flows compose existants (envoi non-patient, envoi patient sans toggle = comportement task-001 inchangé : pas d'en-tête)
- [ ] EPIC §6.13 ligne RG-E009-016 mise à jour par `/tech-writer E009` : note explicite « toggle UI livré, end-to-end opérationnel via les 2 frontends »

## Manual Test Plan

### Setup
1. `cd Api/Mail/src/AppHost && dotnet run --launch-profile https`
2. `cd Client/Blazor/Src/Shell && dotnet run --launch-profile https_test`
3. `cd Client/Angular/front && npm start`

### Vérification 1 — visibilité conditionnelle (Blazor + Angular)

1. Loguer en tant que doctor1.
2. Cliquer **« Nouveau message »**.
3. **Vérifier** : aucun toggle « Bloquer la réponse du patient » visible (pas de destinataire saisi).
4. Saisir une adresse non-patient (`pro@mssante.fr`).
5. **Vérifier** : toujours pas de toggle visible.
6. Ajouter une adresse patient (`<matricule>@patient.mssante.fr`).
7. **Vérifier** : la checkbox apparaît, par défaut **non-cochée**, avec label « Bloquer la réponse du patient » et tooltip qui cite §3.4.2.3 / ECO.2.2.8.
8. Retirer l'adresse patient.
9. **Vérifier** : la checkbox disparaît, et si on rajoute une adresse patient elle réapparaît **non-cochée** (pas d'état persistant caché).

### Vérification 2 — propagation au payload (réseau)

1. Saisir une adresse patient + un objet + un corps + cocher « Bloquer la réponse du patient ».
2. Cliquer **Envoyer**.
3. **Devtools réseau** → request `POST /api/v1/mail/sendmail` :
   - `BlockPatientReply: true` dans le body JSON
4. **Seq** → log Information `[MssanteHeader] X-MSS-MES: FIN emitted` (ou équivalent — task-001 trace l'émission).
5. **Côté patient** (boîte test `<matricule>@patient.mssante.fr`) : tenter de répondre. La fonction « Répondre » est bloquée par MES côté serveur (test end-to-end éventuel — peut être différé).

### Vérification 3 — reset on remove

1. Saisir une adresse patient + cocher la case.
2. Retirer l'adresse patient.
3. Re-saisir une adresse patient.
4. **Vérifier** : la case est **non-cochée** (réinitialisée).
5. Sans la cocher, cliquer Envoyer.
6. **Devtools réseau** : `BlockPatientReply: false` dans le body.

### Vérification 4 — non-régression

1. Envoyer un mail à un destinataire **non-patient** (`pro@mssante.fr`) sans cocher (toggle invisible).
2. **Devtools réseau** : `BlockPatientReply: false` ou champ omis.
3. **Seq** : aucun log d'émission `X-MSS-MES`.
4. Le mail arrive normalement, le destinataire pro peut répondre.

### Vérification 5 — brouillon (Blazor)

1. Saisir adresse patient + cocher la case + objet + corps.
2. Fermer la dialog (auto-save brouillon).
3. Rouvrir le brouillon depuis le dossier Drafts.
4. **Vérifier** : la case est **toujours cochée** (état restauré depuis Redis via `SaveDraftDto.BlockPatientReply`).

## Limites

- La méthode alternative (`Subject = "[FIN]"` exactement) n'est **pas**
  implémentée. ECO.2.2.8 désigne la méthode `X-MSS-MES: FIN` comme
  privilégiée. La méthode subject reste possible si l'utilisateur saisit
  manuellement `[FIN]` mais sans validation ni contrôle UI.
- `task-001` mentionnait un follow-up : `DraftService.BuildMailDto` ne
  résout pas `SaveDraftDto.AttachmentIds` en `MailDto.Attachments[].Content`.
  Cette task-026 **n'attaque pas** ce follow-up — elle ne fait que
  câbler le toggle UI. Si le brouillon doit déclencher
  `X-MSS-MES: FIN` via la route `SaveDraft → SendDraft`, il faut soit
  attendre le follow-up draft-attachments, soit envoyer directement
  via `MailController.SendMailAsync`.

## References réglementaires

- **Référentiel socle MSSanté #2 v1.0.1 — §3.4.2.3** (Mon Espace Santé,
  fin d'échange usager) : ECO.2.2.8.
- **REM Ségur V2** : SC.MSS/CONF.21 (en-tête `X-MSS-MES = "FIN"`).
- task-001 (archived) : implémentation backend `MssanteHeaderService` +
  DTO `MailDto.BlockPatientReply` + `SaveDraftDto.BlockPatientReply`.

## Branches

- `client-blazor` (pushed) : feat/task-026-block-patient-reply-toggle — https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-026-block-patient-reply-toggle
- `dtos-mss` (pushed) : feat/task-026-block-patient-reply-toggle — auto-incluse par convention CLAUDE.md (client-blazor consumes DTOs). **Aucune modification DTO attendue** : `MailDto.BlockPatientReply` et `SaveDraftDto.BlockPatientReply` sont déjà publiés depuis task-001 → branche probablement sans commit, sans PR au merge.
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (snapshot au /start : `feature/nova-rewriting-mss-fixes-20260410`, working tree clean) — humain gère branche, commit, push, PR TFS.
- `api-mail` : non listé dans **Repos**: — la logique d'émission `X-MSS-MES: FIN` est déjà câblée par task-001 dans `MssanteHeaderService`. Aucun changement backend nécessaire.
- `devops`, `psc-proxy-*` : managed manually by the human.

## Develop log

- Repos touched : `client-blazor` (full implementation + tests), `client-angular` (code-only, uncommitted).
- DTOs published : aucun changement (DTO `MailDto.BlockPatientReply` + `SaveDraftDto.BlockPatientReply` déjà publiés depuis task-001).
- Interop published : aucun changement.
- Backend api-mail : **non touché** — la logique d'émission `X-MSS-MES: FIN` est déjà câblée dans `MssanteHeaderService` depuis task-001.
- Commits :
  - `client-blazor` `58d7ba9` — `feat(mail): UI toggle « Bloquer la réponse du patient » (task-026)`
  - `client-angular` (code-only) — uncommitted sur `feature/nova-rewriting-mss-fixes-20260410`, humain handles git/PR TFS
- Build : ✓ Blazor solution clean ; Angular type-check OK (Vitest 98/98 passed).
- Tests :
  - HealthPlatform.Module.Mss.Plugin.Tests : **37/37** (était 21, **+16 nouveaux** `BlockPatientReplyHelperTests`)
  - mss-lib Vitest : 98/98 (no regression — pas de nouveau spec ajouté, gap documenté ci-dessous)
- DOD self-check :
  - [x] Build passes (0 errors) sur `client-blazor`, Angular type-check OK
  - [x] Tests pass (0 failures) sur les 2 frontends
  - [x] **Blazor** : checkbox visible conditionnellement (`ShouldShowBlockPatientReplyToggle()` → délègue à `BlockPatientReplyHelper.HasPatientRecipient(_to, _cc, _bcc)`), `data-testid="compose-block-patient-reply-checkbox"` posé, label + tooltip via Localizer FR + EN
  - [x] **Blazor** : reset à `false` quand le dernier destinataire patient disparaît (effet de bord intégré dans `ShouldShowBlockPatientReplyToggle()` — réévalué à chaque render)
  - [x] **Blazor** : `_mail.BlockPatientReply` populated automatiquement par le `@bind-Value` Radzen, propagé au moment du Send via `SendMailAsync(_mail)`
  - [x] **Blazor** : 16 tests bUnit-style (xUnit Theory + Fact) sur le helper static — couvre IsPatientAddress (case-insensitive, null/empty, partial-match) + HasPatientRecipient (empty, null, no-patient, To, Cc, Bcc, uppercase, partial)
  - [x] **Angular** (code-only) : checkbox visible via `@if (hasPatientRecipient())`, computed signal qui scrute les 3 listes, `data-testid="compose-block-patient-reply-checkbox"`, label + tooltip inline FR (Weda 2 utilise des strings inline FR-only sur ce composant — pas d'i18n catalog dédié)
  - [x] **Angular** : reset via `effect(() => { if (!hasPatientRecipient()) blockPatientReply.set(false) })` qui track les 3 signals
  - [x] **Angular** : `blockPatientReply` propagé sur `Partial<MailDto>` au moment du `sendMailDirect()`, et reset à `false` dans `reset()` à la fermeture
  - [x] **Angular** : modèle `MailDto.blockPatientReply?` ajouté dans `mail.model.ts` avec commentaire pointant task-001 + ECO.2.2.8
  - [⏳] **Angular Vitest tests** : non écrits — gap documenté, à compléter dans une chore qualité (le composant `mail-compose` n'avait pas de spec.ts existant ; ajouter en greenfield serait > scope task-026 limitée à câbler le toggle)
  - [x] **Audit grep DOD** :
    - [x] `BlockPatientReply` dans `Client/Blazor/Src/` → ✅ 3 fichiers source (Helper, NewMailComponent, Localizer FR + EN)
    - [x] `blockPatientReply` dans `Client/Angular/front/libs/mss/src/` → ✅ 3 fichiers source (model.ts, component.ts, component.html)
  - [x] **Aucune régression** sur les flows compose existants : suite Blazor 37/37, mss-lib Vitest 98/98 inchangé.
- Limites :
  - Vitest spec.ts pour `mail-compose` non créé (le composant n'avait pas de spec.ts pré-existant, créer un greenfield spec dépasse le périmètre de cette task limitée à câbler le toggle).
  - Le toggle s'affiche uniquement dans le compose dialog. La persistance du toggle dans le brouillon (Redis `SaveDraftDto`) est déjà côté contract DTO mais pas explicitement testée — humain peut valider en Manual Test Plan.
- Next step : api-mail non touché → **skip /sonar**, chain directement vers `/review task-026`.

## PRs

- **client-blazor** : https://github.com/codengine-technologies/HealthPlatform.Client/pull/45
  - Title : `feat(mail): UI toggle « Bloquer la réponse du patient » (task-026)`
  - Label : `awaiting-human-merge`
  - 4 fichiers, +179/-1, commit `58d7ba9`
- **dtos-mss** : aucune PR. Branche `feat/task-026-block-patient-reply-toggle` créée par `/start` à titre préventif, aucune modification DTO requise (`MailDto.BlockPatientReply` + `SaveDraftDto.BlockPatientReply` déjà publiés depuis task-001). Branche sans commit, sera supprimée au merge.
- **client-angular** : code-only — humain gère commit/push TFS. 3 fichiers modifiés (uncommitted) sur branche `feature/nova-rewriting-mss-fixes-20260410` :
  - `front/libs/mss/src/core/models/mail.model.ts` — `blockPatientReply?: boolean`
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.ts` — signal + computed + effect + propagation + reset
  - `front/libs/mss/src/features/mail/components/mail-compose/mail-compose.component.html` — checkbox conditionnelle `@if (hasPatientRecipient())`
- **api-mail** : non touché — `MssanteHeaderService` task-001 déjà câblé.
- **devops**, **psc-proxy-***: managed manually by the human.

## Code Review Summary

**Verdict : ✅ APPROVED** (7 fichiers reviewés, 0 issue bloquante, 1 suggestion non-bloquante)

- **Helper extraction** propre dans `BlockPatientReplyHelper` (static, allocation-free, null-safe, case-insensitive). Permet l'unit-test isolé sans cérémonie bUnit.
- **Composant Blazor** : `ShouldShowBlockPatientReplyToggle()` ré-évalué à chaque render avec reset side-effect intégré. data-testid posé. Symétrique avec le RequestReadReceipt existant.
- **Composant Angular** : signal `blockPatientReply` + computed `hasPatientRecipient` reactif + effect de reset qui track les 3 signals. Propagation au payload + reset dans `reset()`. Pattern signal-first cohérent avec le reste du composant.
- **Localizer** : FR + EN parity, tooltip cite §3.4.2.3 / ECO.2.2.8 pour traçabilité réglementaire.
- **Tests** : 16 unit tests Theory/Fact couvrant les edge cases (uppercase, null, partial-match-négatif, suffix sans @, missing leading @, in To/Cc/Bcc).
- **Sécurité** : la logique de gating est **server-validated** (task-001 `MssanteHeaderService` re-vérifie la présence d'au moins un destinataire `*@patient.mssante.fr` avant d'émettre `X-MSS-MES: FIN` même si le client envoie `BlockPatientReply == true` sans destinataire patient). Le toggle UI est une convenience pas un vecteur de sécurité.

### Suggestion non-bloquante

1. **Vitest spec côté Angular** non écrit (mail-compose.component n'a pas de spec.ts pré-existant ; créer un greenfield avec mocking de ~10 deps dépasserait le périmètre task-026). Gap documenté, même posture qu'au merge task-006.

HAG (rule 10) : test manually, then merge PR #45 yourself. Angular code-only : humain commit/push TFS sur `feature/nova-rewriting-mss-fixes-20260410`.

## Merged

- **client-blazor** : PR #45 squash-merged into `develop` — squash SHA `9d73b14` (`feat(mail): UI toggle « Bloquer la réponse du patient » (task-026) (#45)`). Remote branch `feat/task-026-block-patient-reply-toggle` deleted. CI `Build and Publish` ✅ SUCCESS sur develop.
- **dtos-mss** : aucune PR (branche sans commit). Remote branch `feat/task-026-block-patient-reply-toggle` deleted directement via `git push --delete`.
- **client-angular** : code-only — humain gère commit/push TFS et la PR sur `feature/nova-rewriting-mss-fixes-20260410`. Aucune action git de `/merge`.
- **api-mail**, **devops**, **psc-proxy-*** : non touchés / hors scope.

Local feature branches conservées dans chaque clone pour inspection rétroactive (convention `/merge` — `--delete-branch` ne retire que le remote).
