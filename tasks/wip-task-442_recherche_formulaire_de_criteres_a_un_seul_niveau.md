# todo-task-442.md — Recherche : formulaire de critères à un seul niveau

**Repos**: client-angular, api-mail
**Dependencies**: aucune
**Epic**: E023
**EpicTitle**: Expérience de recherche
**Priorité**: EPIC E023, demandée par l'humain le 2026-11-10. Première marche de la refonte de la recherche : un
formulaire de critères simple, qu'on remplit puis qu'on lance, et qui se ferme pour laisser voir les résultats.

> **Origine.** Analyse du 2026-11-10 avec l'humain, à partir de la recherche d'Outlook 365 : toutes les propositions
> ont été acceptées. weda2 d'abord ; le mobile suit le même modèle (task-450). `api-mail` figure dans les Repos pour le
> catalogue e2e.

## Ce qui est établi

Lecture du code au 2026-11-10 (`Client/Angular/front/libs/mss/src/features/mail/components/mail-search/`) :

- La fenêtre sous la barre de recherche empile l'historique, des filtres rapides (Statut, Contenu médical, Période),
  puis un **second panneau** « Recherche avancée » (De, À ou Cc, Objet, Type de document), atteint par un bouton et
  quitté par une flèche retour.
- Le bouton « Rechercher » n'existe que dans le panneau avancé. Ailleurs, la recherche part sur Entrée ou au clic d'un
  filtre : le médecin ne sait pas quand elle part.
- Rien ne remet le formulaire à vide sans effacer aussi la recherche affichée : la croix de la barre fait les deux.
- Les boutons sont des `<button>` stylés localement, pas les composants du design system (`ds-*`).

## Objective

Le médecin ouvre la fenêtre de recherche, compose ses critères dans **un seul formulaire**, puis lance la recherche.
La fenêtre se ferme et laisse voir les résultats.  
Si le médecin clique en dehors de cette fenètre, elle se ferme automatiquelent.

Règles :
- **Un seul niveau** : les filtres rapides et les critères avancés (De, À ou Cc, Objet, Type de document, Période,
  Statut, Contenu médical) sont dans le même formulaire, groupés par sections titrées. Plus de second panneau ni de
  flèche retour.
- **Deux boutons en bas du formulaire**, composants du design system :
  - **« Lancer la recherche »** (bouton principal) ;
  - **« Réinitialiser les paramètres »** (bouton secondaire).
- **Rien ne part avant « Lancer »** : un clic sur un filtre le coche ou le décoche, sans lancer de recherche. La touche
  Entrée dans le champ de saisie équivaut à « Lancer la recherche ».
- **Lancer ferme la fenêtre** et affiche les résultats.
- **« Lancer » sans aucun critère** : le bouton est inactif tant que ni texte ni critère n'est saisi.
- **« Réinitialiser les paramètres »** vide le texte et tous les critères du formulaire. Il ne ferme pas la fenêtre,
  ne lance rien, et ne touche pas aux résultats déjà affichés.
- **Rouvrir la fenêtre** après une recherche montre les critères de la recherche affichée, pour les modifier.
- **Fermer sans lancer** (Échap, clic en dehors) : les critères modifiés et non lancés sont abandonnés ; la recherche
  affichée ne change pas.
- **Historique des recherches** : inchangé, en tête de la fenêtre, jusqu'à task-449 qui le déplace dans les
  suggestions.
- La croix de la barre garde son rôle actuel (effacer la recherche affichée) jusqu'à task-445, qui la remplace par
  « Fermer la recherche ».

### Hors périmètre

- Les nouveaux critères médicaux : task-443.
- Le mode « Résultats de recherche » : task-445.
- Le mobile : task-450.

## Definition of Done

- [ ] Build passes (0 errors) : weda2 (`nx build weda2`)
- [ ] Tests pass (0 failures) : `nx test weda2`, `nx test mss-lib` (ligne « Tests » lue : des specs ont bien tourné)
- [ ] Tests de composant : un filtre cliqué ne lance aucune recherche ; « Lancer » lance une recherche portant
      **tous** les critères cochés et ferme la fenêtre ; Entrée équivaut à « Lancer » ; « Lancer » inactif sans critère ;
      « Réinitialiser » vide tout sans fermer ni lancer, et laisse les résultats affichés ; fermer sans lancer abandonne
      les critères modifiés ; rouvrir montre les critères de la recherche affichée ; chacun vu rouge par mutation
- [ ] Boutons « Lancer la recherche » et « Réinitialiser les paramètres » réalisés avec les composants `ds-*` du design
      system (aucun bouton stylé localement pour ces deux actions)
- [ ] **Scénario e2e** : `E2E-SEARCH-001` passe en **version 2** dans `Api/Mail/e2e/scenarios.yml` — titre « Composer
      ses critères puis lancer la recherche », attendu : cocher un filtre ne lance rien ; « Lancer la recherche » ferme
      la fenêtre et affiche les résultats ; « Réinitialiser les paramètres » vide le formulaire. Clients : angular
      requis, mobile requis avec **divergence temporaire** (raison : « le mobile adopte le formulaire à un seul niveau
      avec la refonte mobile de la recherche », tache : task-450). Implémenté dans weda2, vu rouge par mutation ;
      `E2E-SEARCH-002` et `003` restent verts
- [ ] `data-testid` sur chaque élément interactif ajouté ou déplacé (`mail-search-launch`, `mail-search-reset`, sections)
- [ ] Aucune chaîne en dur hors des conventions de libellés de weda2 ; aucune donnée de santé dans les libellés
- [ ] client-angular : code-only, aucun commit (l'humain gère la branche et TFS)
- [ ] **Prévention (règle d'or)** : consigne dans `conventions/angular.md` : un formulaire de critères ne déclenche
      rien avant son bouton d'action ; ses boutons d'action sont ceux du design system

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail/src/AppHost && dotnet run`. Lancer weda2 : `cd Client/Angular/front && npm start`.
2. Se connecter avec la CPS de test, ouvrir la Boîte de réception, cliquer dans la barre de recherche.
3. Vérifier :
   - un seul formulaire, sans bouton « Recherche avancée » ni flèche retour ; les champs De, À ou Cc, Objet et Type de
     document sont dans le formulaire ;
   - en bas, « Lancer la recherche » et « Réinitialiser les paramètres », au style du design system ;
   - « Lancer » est grisé tant que rien n'est saisi.
4. Cocher « Non lus » puis « Pièces jointes » : la liste ne change pas.
5. Taper `psoriasis`, cliquer « Lancer la recherche » : la fenêtre se ferme, les résultats s'affichent.
6. Rouvrir la fenêtre : `psoriasis`, « Non lus » et « Pièces jointes » sont présents. Cliquer « Réinitialiser les
   paramètres » : le formulaire est vide, la fenêtre reste ouverte, les résultats derrière n'ont pas changé.
7. Appuyer sur Échap : la fenêtre se ferme, les résultats de `psoriasis` sont toujours là.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — ergonomie de la recherche
- **Exigences DSR honorées** : non applicable — aucune exigence DSR ne porte sur la forme du formulaire
- **INS** : non applicable — aucun identifiant patient manipulé par le formulaire
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : inchangées — accès à la boîte ouvert par le verdict de l'opérateur MSSanté (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé — chaque recherche lancée est tracée côté serveur (`MailSearch`) au nom de la personne
  réelle, 3 653 jours ; cocher un filtre sans lancer n'est pas un acte et n'est pas tracé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable au client — aucune donnée stockée
- **AIPD / impact RGPD** : inchangé

## Branches
- `api-mail` (pushed) : feat/task-442-recherche-formulaire-de-criteres-a-un — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-442-recherche-formulaire-de-criteres-a-un (catalogue e2e)
- `client-angular` (code-only) : la forge écrit le code sur la branche extraite dans `Client/Angular/` (au `/start` : `feature/nova-mss-weda-integration`, propre) — l'humain gère branche, commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-442 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 14 s | — | — | — | — |
| **Total cycle** | | **14 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
