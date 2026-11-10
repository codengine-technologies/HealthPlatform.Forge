# todo-task-448.md — Recherche : sélectionner tous les résultats et actions groupées

**Repos**: api-mail, dtos-mss, client-angular
**Dependencies**: done-task-445 (mode résultats)
**Epic**: E023
**Priorité**: EPIC E023, demandée par l'humain le 2026-11-10. Le médecin trie sa boîte à partir d'une recherche :
« tous les messages de ce laboratoire, marqués lus et archivés » en un geste.

> **Origine.** Analyse du 2026-11-10 (case « tout sélectionner » d'Outlook, « sélectionner les N conversations
> correspondant à cette recherche » de Gmail). Décision de l'humain du 2026-11-10 : actions groupées limitées à
> marquer lu ou non lu, étoile, déplacer, supprimer (mise à la corbeille). **Hors lot, par sécurité clinique** :
> l'acquittement de biologie en masse (acquitter atteste que le médecin a pris connaissance de **chaque** résultat) et
> le rattachement en masse à un patient (risque d'identito-vigilance).

## Ce qui est établi

- weda2 a un mode sélection dans la liste (`mail-list.component`) avec « Tout », Lu, Non lu, Favori, Déplacer : il ne
  porte que sur les messages **chargés** à l'écran.
- La règle 14 impose que chaque acte sur un message soit imputé à la personne réelle.

## Objective

Dans le mode « Résultats de recherche », le médecin sélectionne tous les résultats, y compris ceux qui ne sont pas
encore chargés, et leur applique une action groupée.

Règles :
- **Case « Tout sélectionner »** dans l'en-tête des résultats : elle sélectionne les résultats chargés, puis propose
  « Sélectionner les N résultats de la recherche » (N = total rendu par le serveur).
- **Actions** : Marquer comme lu, Marquer comme non lu, Ajouter ou retirer l'étoile, Déplacer vers un dossier,
  Supprimer (mise à la Corbeille). La suppression définitive n'est pas proposée.
- **Confirmation explicite** quand l'action porte sur plus de messages qu'il n'en est chargé, ou sur plus de 50
  messages : « Déplacer 342 messages vers Archives ? ».
- **Périmètre figé** : l'action porte exactement sur les résultats comptés au moment de la confirmation ; un message
  arrivé depuis n'est pas concerné.
- **Plafond** : 2 000 messages par action ; au-delà, le médecin est invité à affiner sa recherche.
- **Progression et compte rendu** : une barre de progression au-delà de 100 messages ; à la fin, « 340 messages
  déplacés, 2 en échec », avec la possibilité de réessayer les échecs. Une action partielle n'est jamais présentée comme
  complète.
- Après l'action, la recherche est relancée (un message déplacé hors portée ou à la Corbeille disparaît des résultats).
- **Règle 14** : chaque message touché est tracé **individuellement**, au nom de la personne qui a agi (RPPS, nom PSC,
  rôle), avec l'action et l'objet. Un délégataire ou un membre agit comme le titulaire, et la trace le dit.

### Hors périmètre

- Acquittement de biologie en masse, rattachement en masse à un patient, suppression définitive : exclus par décision
  de l'humain.
- Le mobile : task-451.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`, `HealthPlatform.Dtos.Mss.csproj`, weda2 (`nx build weda2`)
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`, `nx test weda2`, `nx test mss-lib`
- [ ] Tests unitaires du service d'action groupée : chaque action, plafond, échecs partiels, périmètre figé (≥ 1 test par
      branche)
- [ ] **Tests d'intégration de bout en bout (règle 1b)** sur la route d'action groupée, lus dans la réponse réelle et en
      base, chacun vu rouge par mutation :
      - 120 résultats (plus d'une page) déplacés vers « Archives » : les 120 sont dans « Archives », aucun autre message
        n'a bougé ; la réponse compte 120 succès ;
      - marquer lu : les 120 portent le drapeau lu ;
      - un message supprimé entre la confirmation et l'exécution : 119 succès, 1 échec nommé, aucune erreur globale ;
      - **périmètre figé** : un message correspondant arrivé après la confirmation n'est pas déplacé ;
      - **cas d'échec** : 2 001 messages → 400 en `ProblemDetails`, rien n'est modifié ; boîte sans verdict de
        l'opérateur → refus, rien n'est modifié
- [ ] **Test d'intégration règle 14** : deux personnes rattachées à la même boîte (titulaire et délégataire) ; le
      délégataire déplace 3 résultats ; la trace porte **3 entrées au nom du délégataire** (RPPS, nom, rôle
      « délégataire »), aucune au nom du titulaire ni de la boîte
- [ ] Contrat `dtos-mss` publié (rétrocompatible) et consommateurs .NET mis à jour ; types TypeScript de weda2 alignés
- [ ] Tests de composant weda2 : « Tout sélectionner » puis « Sélectionner les N résultats », confirmation, progression,
      compte rendu partiel, relance de la recherche ; chacun vu rouge par mutation
- [ ] **Scénario e2e** `E2E-SEARCH-012` v1 : « Traiter tous les résultats d'une recherche » — attendu : après
      « Sélectionner les N résultats » et confirmation, les N messages sont marqués lus, y compris ceux qui n'étaient pas
      chargés. Clients : angular requis, mobile requis avec **divergence temporaire** (raison : « la sélection de tous
      les résultats arrive sur le mobile avec la refonte mobile », tache : task-451). Implémenté dans weda2, vu rouge
      par mutation
- [ ] `data-testid` sur chaque élément interactif ajouté
- [ ] Évènements PGSSI-S journalisés : une trace par message et par action, au nom de la personne réelle
- [ ] Aucune donnée de santé en clair dans les logs (objets, expéditeurs, termes)
- [ ] client-angular : code-only, aucun commit
- [ ] **Prévention (règle d'or)** : consigne dans `conventions/csharp.md` : une action groupée trace chaque objet touché
      au nom de son auteur, et rend le détail de ses échecs

## Manual Test Plan

1. Lancer le backend sur le corpus fictif : `cd Api/Mail/src/AppHost && dotnet run`, puis le seed de référence. Lancer
   weda2 : `cd Client/Angular/front && npm start`.
2. Rechercher l'expéditeur d'un laboratoire du corpus (plus de 50 messages).
3. Cocher « Tout sélectionner », puis « Sélectionner les N résultats de la recherche ».
4. Cliquer « Marquer comme lu » : une confirmation annonce N messages. Confirmer : progression, puis « N messages
   marqués comme lus ».
5. « Fermer la recherche », ouvrir la Boîte de réception : les messages du laboratoire, y compris les plus anciens, sont
   lus.
6. Rechercher à nouveau, tout sélectionner, « Déplacer » vers « Archives » : ils disparaissent des résultats en portée
   « Dossier courant » et apparaissent dans « Archives ».
7. Se connecter avec la carte du délégataire, déplacer 3 résultats ; ouvrir le journal de la boîte : 3 entrées au nom du
   délégataire.
8. Vérifier qu'aucune action « Acquitter » ni « Rattacher à un patient » n'est proposée en sélection.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — ergonomie de la messagerie
- **Exigences DSR honorées** : non applicable — l'imputabilité des actes suit la PGSSI-S (référentiel d'imputabilité)
  et la règle 14 de la plateforme
- **INS** : non applicable — aucun rattachement patient en masse (exclu)
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : verdict de l'opérateur MSSanté requis (règle 14) ; titulaire, délégataire et membre disposent des
  mêmes actions groupées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : une trace par message et par action (lecture marquée, étoile, déplacement, mise à la Corbeille),
  au nom de la personne réelle (RPPS, nom PSC, rôle), avec la boîte, l'instant, l'action et l'objet ; 3 653 jours ;
  visibles de toute personne rattachée à la boîte
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — base de la boîte et serveur IMAP de l'opérateur, inchangés
- **AIPD / impact RGPD** : inchangé — mêmes actions qu'à l'unité
