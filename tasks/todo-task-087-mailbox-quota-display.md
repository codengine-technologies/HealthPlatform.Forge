# todo-task-087.md — Affichage du quota d'occupation de la boîte MSSanté

**Repos**: api-mail, client-blazor, client-angular
**Epic**: E009

## Objective

Donner au professionnel de santé une **visibilité sur l'occupation globale de sa
boîte MSSanté** : espace utilisé, quota total et pourcentage de remplissage.
Inspiré de l'affichage de quota IMAP de Roundcube. Cas d'usage : anticiper une
boîte pleine (qui bloquerait la réception de nouveaux courriers de santé), sans
attendre un rejet d'envoi côté correspondant.

**Périmètre d'affichage (décision PO 2026-06-14)** : **quota global uniquement**,
affiché en **pied du volet liste des dossiers** (`FolderList`) des deux fronts.
**Pas de quota par dossier** — la liste des dossiers reste inchangée, on ajoute
seulement un footer. Voir la section *Analyse front & emplacement* ci-dessous.

## Comportement attendu

- Le backend interroge le quota IMAP (extension `QUOTA` / `QUOTAROOT`) de la
  boîte du PS et expose espace utilisé, quota total et pourcentage.
- Une **jauge linéaire** d'occupation globale est affichée en **pied du volet
  dossiers** (footer du `FolderList`), façon Roundcube : `Utilisé X Go / Y Go · Z %`.
- **Deux paliers d'alerte visuelle** : la barre vire à l'**ambre dès ≥ 80 %** et
  au **rouge dès ≥ 90 %** (boîte presque pleine, réception bientôt bloquée).
- Si le serveur IMAP n'annonce pas l'extension QUOTA, le footer affiche
  proprement « Quota non disponible » sans erreur bloquante (état discret,
  pas de notification d'erreur).
- La valeur est rafraîchie au chargement de la messagerie (et sur rafraîchissement
  manuel), sans appel coûteux à chaque action — le quota évolue lentement.

## Gherkin

```gherkin
Feature: Affichage du quota de la boîte MSSanté

  Scenario: Boîte avec quota disponible
    Given une boîte MSSanté dont le serveur annonce un quota
    When le médecin consulte sa messagerie
    Then il voit l'espace utilisé, le quota total et le pourcentage de remplissage

  Scenario: Avertissement boîte qui se remplit
    Given une boîte remplie entre 80 % et 90 % de son quota
    When le médecin consulte sa messagerie
    Then la jauge passe en alerte modérée (ambre) pour l'inviter à faire de la place

  Scenario: Alerte boîte presque pleine
    Given une boîte remplie à 90 % ou plus de son quota
    When le médecin consulte sa messagerie
    Then la jauge passe en alerte forte (rouge) signalant que la boîte est presque pleine

  Scenario: Serveur sans extension de quota
    Given un serveur IMAP qui n'annonce pas de quota
    When le médecin consulte sa messagerie
    Then le pied du volet dossiers indique que le quota n'est pas disponible
    And aucune erreur bloquante n'est affichée
```

## Analyse front & emplacement (décision PO 2026-06-14)

Analyse des deux fronts effectuée avant figeage. **Cible : le pied (footer) du
volet liste des dossiers**, dans les deux fronts. Jauge **linéaire** (plus
lisible qu'une circulaire pour un % de remplissage). **Quota global uniquement,
aucun quota par dossier.**

**Blazor** :
- Composant cible : `FolderListComponent.razor`
  (`Src/Modules/Mss/Plugin/Components/`). Ajouter un footer sous le
  `RadzenSplitter` (dans `.folder-list-wrapper`) — pas de footer aujourd'hui.
- Données : nouveau service/appel (cf. endpoint backend) consommé via un
  ViewModel, à la manière de `FolderListViewModel` + `IFolderService`.
- Réutiliser : `RadzenProgressBar` (linéaire) ou une barre CSS simple ;
  `Localizer` pour les libellés (clés `MailboxQuota*`) ; tokens CSS
  `--mss-*` ; `data-testid` kebab-case (ex. `mailbox-quota`).

**Angular** :
- Composant cible : `MailFolderListComponent`
  (`libs/mss/src/features/mail/components/mail-folder-list/`). Ajouter un
  footer après les sections Dossiers/Tags — pas de footer aujourd'hui.
- Données : étendre `MssApiService` (ex. `getMailboxQuota()`) + signal dans
  `MailStateService` (ou service dédié), pattern signals-first.
- **Réutiliser le patron `SyncProgressWidget`** (`libs/mss/src/ui/`) — déjà un
  widget de statut de boîte avec état « indisponible » et textes `computed()` ;
  idéalement **grouper la jauge quota au même endroit** (cohérence des
  indicateurs de boîte). Tokens `var(--ds-color-*)` du `@weda/design-system` ;
  `data-testid` kebab-case.
- **i18n** : le module MSS Angular **n'utilise pas ngx-translate** — libellés
  FR écrits en dur dans le template, valeurs dynamiques via `computed()`
  (ex. `2,5 Go / 15 Go · 17 %`). Suivre cette convention existante (voir DOD).

## Definition of Done

- [ ] Build passes sur chaque repo listé (0 erreur)
- [ ] Endpoint backend `GET account/quota` (ou équivalent) renvoyant espace utilisé, quota total, pourcentage et un indicateur « disponible/non disponible »
- [ ] Lecture du quota via l'extension IMAP QUOTA (MailKit) ; dégradation propre si non supportée
- [ ] >= 1 test unitaire par comportement (quota disponible, quota indisponible, calcul du pourcentage, palier ambre ≥80 %, palier rouge ≥90 %)
- [ ] >= 1 test d'intégration de l'endpoint (cas disponible + cas non supporté)
- [ ] Blazor : footer de jauge **linéaire** ajouté à `FolderListComponent.razor` (espace utilisé / quota / %), état « Quota non disponible », deux paliers visuels (ambre ≥80 %, rouge ≥90 %), libellés via `Localizer` (clés `MailboxQuota*`, aucune chaîne en dur), `data-testid` (ex. `mailbox-quota`)
- [ ] Angular : footer de jauge **linéaire** ajouté à `MailFolderListComponent` (idem), état « Quota non disponible », deux paliers visuels (ambre ≥80 %, rouge ≥90 %), `data-testid` ; **libellés FR dans le template + valeurs dynamiques via `computed()`** (le module MSS Angular n'utilise pas ngx-translate — suivre la convention existante), réutiliser le patron `SyncProgressWidget` et les tokens `var(--ds-color-*)`
- [ ] Erreurs renvoyées en `ProblemDetails` (RFC 7807) via le `GlobalExceptionHandler` (règle 12)
- [ ] Aucune donnée de santé en clair dans les logs (seules des métriques de volumétrie sont loggées)

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Lancer Blazor : `cd Client/Blazor && dotnet run`
- Lancer Angular : `cd Client/Angular && npm start`
- Se connecter à une boîte MSSanté de test
- Vérifier l'affichage de la jauge (espace utilisé / quota / pourcentage)
- Simuler / utiliser une boîte > 90 % → vérifier l'alerte visuelle
- Utiliser une boîte dont le serveur n'annonce pas de quota → vérifier le
  message « quota non disponible » sans erreur bloquante

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR spécifique — supervision de la boîte
- **Exigences DSR honorées** : non applicable — n'altère pas le transport MSSanté ni le contenu des courriers
- **INS** : non applicable — donnée d'infrastructure (volumétrie), aucune donnée patient
- **Authentification PS** : inchangé — quota lu pour la boîte du PS authentifié
- **Habilitations** : lecture du quota limitée à la boîte du PS authentifié
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable — lecture d'une métrique technique (option : journaliser un seuil d'alerte franchi)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement existant ; le quota est une métadonnée de volumétrie, pas une donnée de santé
- **AIPD / impact RGPD** : inchangé — aucune donnée personnelle nouvelle traitée
