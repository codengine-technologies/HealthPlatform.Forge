# todo-task-054-opt-in-remove-rpps-field.md — Retrait du champ RPPS de l'opt-in MSSanté (Angular + Blazor)

**Repos**: client-blazor, client-angular
**Dependencies**: archived-task-049 (extraction server-side de `mssRpps` depuis le PSC token au moment de l'opt-in — le champ formulaire est désormais redondant), archived-task-048 (cross-check qui consomme `mssRpps` côté `api-mail`)
**Epic**: E009

## Objectif

Retirer le champ « Numéro RPPS / ADELI » du formulaire d'opt-in MSSanté
sur les deux frontends (Angular et Blazor). Depuis task-049, le proxy
Keycloak extrait `sub` et `SubjectNameID` directement du PSC token de
la session serveur au moment de l'opt-in et les persiste comme
attributs utilisateur `mssSub` / `mssRpps`. Le champ texte côté
frontend ne contribue à rien : sa valeur n'est envoyée nulle part par
le service `MssOnboardingService` (Angular) ni par le composant
`MailSetup` (Blazor) — elle est silencieusement ignorée. Demander au
praticien de re-saisir un identifiant déjà connu côté serveur est à la
fois inutile et dégradant pour l'UX.

### Comportement attendu après la task

- À l'ouverture de l'écran d'opt-in (`/mss/setup` côté Angular,
  `MailSetup.razor` côté Blazor), le praticien voit **un seul champ** :
  son adresse MSSanté candidate (label « Adresse MSSanté » ou
  équivalent existant).
- Aucun champ RPPS / ADELI n'est affiché, aucune validation `^\d{9}(\d{2})?$`
  n'est appliquée.
- Le bouton « Valider » / « Continuer » devient actif dès que l'email
  saisi est syntaxiquement valide (`Validators.email`,
  `Validators.maxLength(254)`).
- Le flow de soumission reste **strictement identique** : sonde IMAP via
  `POST /api/v1/account/mss-imap-test`, puis persistance côté proxy
  Keycloak via `PUT /v1/admin/mss-profile` avec le payload
  `{ email: <adresse> }`. Aucun changement de contrat HTTP.
- L'écran de succès et le bouton « Se reconnecter maintenant » sont
  inchangés.
- Aucun changement côté `api-mail` ni côté `dtos-mss`.

### Hors scope

- ❌ Modification du contrat HTTP ou des services backend.
- ❌ Changements esthétiques sur le formulaire au-delà du retrait du
      champ (la mise en page se resserre naturellement, mais aucun
      restyle volontaire).
- ❌ Migration / réécriture des composants vers une autre librairie de
      formulaires.
- ❌ Suppression côté Blazor des clés de localisation `MssOnboarding_RppsLabel`
      / `MssOnboarding_RppsPlaceholder` si elles sont utilisées ailleurs ;
      sinon, elles partent avec le champ.

## Scope détaillé

### `client-angular` (mode code-only — humain gère git + PR TFS)

Fichiers concernés (à confirmer pendant l'implémentation) :
- `libs/mss/src/features/setup/mss-setup.component.ts` : retirer
  `RPPS_PATTERN`, retirer le contrôle `rpps` du `setupForm`, ajuster les
  imports si nécessaire.
- `libs/mss/src/features/setup/mss-setup.component.html` : retirer le
  bloc `<label>` + `<input>` + message d'erreur du champ RPPS.
- `libs/mss/src/features/setup/mss-setup.component.spec.ts` : retirer
  les assertions et les utilitaires de test qui peuplaient `rppsInput`.
  Mettre à jour le helper de remplissage du formulaire en conséquence.
- Aucun changement attendu sur `mss-onboarding.service.ts` (la
  signature ne change pas).

### `client-blazor`

Fichiers concernés (à confirmer pendant l'implémentation) :
- `Src/Modules/Mss/Plugin/Pages/MailSetup.razor` : retirer le bloc
  `<label>` + `<InputText>` + `<ValidationMessage>` du champ RPPS ;
  retirer la propriété `Rpps` du modèle interne + les annotations
  `[Required]` / `[RegularExpression]` associées.
- `tests/HealthPlatform.Module.Mss.Plugin.Tests/MailSetupPageTests.cs` :
  retirer les assertions sur le champ RPPS et les flows qui le
  peuplaient pour franchir la validation.
- `Src/Modules/Mss/Domain/Globalization/Localizer.cs` : retirer les clés
  `MssOnboarding_RppsLabel` / `MssOnboarding_RppsPlaceholder` (FR + EN)
  si elles ne sont plus référencées ailleurs (vérifier par grep).

## Definition of Done

- [ ] **Blazor** : `MailSetup.razor` n'affiche plus de champ RPPS. La
      propriété `Rpps` du modèle est supprimée avec ses annotations.
- [ ] **Angular** : `MssSetupComponent` ne déclare plus de contrôle
      `rpps` dans le `setupForm`. Le pattern `RPPS_PATTERN` est
      supprimé. Le template HTML ne contient plus le bloc RPPS.
- [ ] **Blazor — tests** : `MailSetupPageTests` reste vert sans les
      assertions sur le champ RPPS ; les helpers de remplissage sont
      adaptés. Aucun test ne dépend encore de la présence du champ.
- [ ] **Angular — tests** : `mss-setup.component.spec.ts` reste vert
      sans les utilitaires `rppsInput`. La couverture du composant
      ne régresse pas.
- [ ] **Blazor — Localizer** : les clés `MssOnboarding_RppsLabel` et
      `MssOnboarding_RppsPlaceholder` sont supprimées (FR + EN) si
      aucun autre composant ne les référence. Vérification par grep
      explicite dans la task de review.
- [ ] **Aucune régression du flow d'opt-in** : la sonde IMAP et la
      persistance proxy Keycloak fonctionnent à l'identique, vérifié
      par les tests existants qui exercent le bouton « Valider ».
- [ ] **Aucun changement** sur `api-mail`, `dtos-mss`, ou tout autre
      repo backend.
- [ ] **Build Blazor** : `dotnet build HealthPlatform.Client.sln` → 0
      erreur.
- [ ] **Tests Blazor** : `dotnet test HealthPlatform.Client.sln` → 0
      failure.
- [ ] **Build Angular** : `npm run build` côté `Client/Angular/front/`
      → 0 erreur.
- [ ] **Tests Angular** : `npm test` côté `Client/Angular/front/` →
      tous verts (suite mss-lib).
- [ ] **Lint Angular** : `nx affected -t lint --projects=tag:scope:mss
      --fix` passe sans erreur résiduelle bloquante.
- [ ] **PR Blazor** ouverte sur `feat/task-054-opt-in-remove-rpps-field`,
      labellisée `awaiting-human-merge`.
- [ ] **Angular** (code-only) : code uncommitted sur la branche que le
      humain a checked out dans `Client/Angular/` ; le humain gère
      commit/push TFS et PR.

## Manual Test Plan

> Validation **iso-fonctionnelle** : le flow d'opt-in doit aboutir au
> même résultat fonctionnel qu'aujourd'hui (sonde IMAP OK → persistance
> proxy → écran « Se reconnecter maintenant »), avec un formulaire
> simplifié à un seul champ.

### Setup commun
- Image `client-blazor` issue de `feat/task-054-…` déployée localement
  (ou `dotnet run` côté `Client/Blazor/`).
- Code Angular `feat/task-054-…` checked out localement et `npm start`
  côté `Client/Angular/front/`.
- Compte praticien MSSanté de test qui n'a **jamais** opt-in (JWT KC
  sans `mssEmail`).

### Cas 1 — Opt-in nominal Blazor
1. Naviguer vers `/Mss/Setup` après authentification PSC.
2. Constat attendu : le formulaire affiche **uniquement** le champ
   « Adresse MSSanté » + le bouton « Valider ». Aucun champ RPPS visible.
3. Saisir une adresse MSSanté valide (test op) → cliquer « Valider ».
4. La sonde IMAP réussit, le proxy Keycloak persiste, l'écran de
   succès s'affiche avec le bouton « Se reconnecter maintenant ».
5. Cliquer le bouton → redirection vers le logout host.
6. Re-login PSC → le JWT KC porte désormais `mssEmail`, `mssSub`,
   `mssRpps` (vérifié par jwt.io sur l'access token).

### Cas 2 — Opt-in nominal Angular
Idem cas 1 mais via l'app Angular (`/mss/setup`).

### Cas 3 — Erreur IMAP Blazor
1. Saisir une adresse dont le domaine est invalide
   (`x@inexistant.fr`).
2. Constat attendu : message d'erreur typé (`MailboxNotFound` ou
   `HostUnreachable`), le bouton « Valider » redevient cliquable, le
   champ email reste éditable. Aucun champ RPPS à corriger.

### Cas 4 — Erreur IMAP Angular
Idem cas 3 sur l'app Angular.

### Cas 5 — Validation email manquante / mal formée
1. Soumettre le formulaire vide → message d'erreur « Email requis »
   sur le champ email. Aucun message d'erreur RPPS.
2. Saisir `pas-un-email` → message d'erreur « Email invalide ».
3. Saisir une adresse de plus de 254 caractères → message d'erreur
   « Email trop long ».

### Cas 6 — Iso-fonctionnel après merge des deux frontends
Vérifier qu'un utilisateur Weda (Blazor) et un utilisateur autonome
(Angular) ont **exactement la même expérience** au moment de l'opt-in :
un champ, un bouton, un écran de succès. Aucune divergence UX.
