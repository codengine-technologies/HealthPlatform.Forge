# todo-task-447.md — Recherche : portée « tous les dossiers » et tri

**Repos**: api-mail, dtos-mss, client-angular
**Dependencies**: done-task-445 (mode résultats)
**Epic**: E023
**Priorité**: EPIC E023, demandée par l'humain le 2026-11-10. Un compte rendu peut avoir été classé n'importe où : la
recherche doit le trouver sans que le médecin sache dans quel dossier il est rangé.

> **Origine.** Analyse du 2026-11-10 (sélecteur « Tous les dossiers » et tri « La plus récente » d'Outlook). Décision de
> l'humain : tous les dossiers par défaut ; pertinence par défaut avec bascule « Les plus récents » ; les résultats
> proches par le sens restent toujours à part.

## Ce qui est établi

- La recherche porte sur le dossier courant (`folderPath`) ; la règle RG-E022-05 (« une recherche dans un dossier ne rend
  que des messages de ce dossier ») est vérifiée en continu par task-438.
- Le serveur ordonne par pertinence (groupes, puis section proches, task-439 et task-440). Aucun tri par date n'est
  proposé.

## Objective

Le médecin cherche par défaut dans toute sa boîte, peut restreindre au dossier courant, et choisit l'ordre des
résultats.

Règles :
- **Sélecteur de portée** en tête de la barre de recherche, deux choix :
  - **« Tous les dossiers »** (défaut) : tous les dossiers de la boîte, **sauf la Corbeille et les Indésirables** ;
  - **« Dossier courant »** : le dossier ouvert au moment de la recherche (RG-E022-05 inchangée).
  - Depuis la Corbeille ou les Indésirables, « Dossier courant » est le défaut.
- La portée choisie est une étiquette du mode résultats (task-445) ; la changer relance la recherche.
- **Tri**, dans l'en-tête des résultats :
  - **« Pertinence »** (défaut) : l'ordre du serveur, par groupes puis proches ;
  - **« Les plus récents »** : les résultats exacts (tous les mots et une partie des mots, réunis) triés par date
    d'envoi décroissante, **par le serveur**, puis la partie « Résultats proches » à part, elle aussi par date.
  - Le tri est fait par le serveur sur l'ensemble des résultats, pas sur la page affichée ; « Voir plus » suit le tri.
- La portée et le tri sont rejoués par l'historique des recherches.
- **Règle 14 inchangée.**

### Hors périmètre

- Le mobile : task-451.
- Les dossiers de recherche enregistrés : hors lot.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`, `HealthPlatform.Dtos.Mss.csproj`, weda2 (`nx build weda2`)
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`, `nx test weda2`, `nx test mss-lib`
- [ ] Tests unitaires : portée par défaut, exclusion Corbeille et Indésirables, tri par date sur les exacts réunis puis
      les proches (≥ 1 test par branche)
- [ ] **Tests d'intégration de bout en bout (règle 1b), `POST /api/v1/Search/semantic`**, sur le corpus fictif, lus dans
      la réponse réelle (`Hits` et leur `FolderPath`), chacun vu rouge par mutation :
      - **tous les dossiers** : un message rangé dans « Archives » est trouvé depuis une recherche sans dossier ; un
        message de la Corbeille ne l'est pas ;
      - **dossier courant** : RG-E022-05 toujours verte ;
      - **les plus récents** : les exacts sont triés par date décroissante sur **l'ensemble** des résultats (le plus
        récent de la page 2 en mode pertinence est en page 1), puis les proches ; aucun proche n'est intercalé ;
      - **cas d'échec** : une valeur de tri inconnue → 400 en `ProblemDetails`
- [ ] Contrat `dtos-mss` publié (rétrocompatible : sans portée ni tri, le comportement d'aujourd'hui) et consommateurs
      .NET mis à jour ; types TypeScript de weda2 alignés
- [ ] Tests de composant weda2 : sélecteur de portée, défaut selon le dossier, étiquette de portée, bascule de tri qui
      relance ; chacun vu rouge par mutation
- [ ] **Scénario e2e** `E2E-SEARCH-011` v1 : « Trouver un message rangé dans un autre dossier » — attendu : depuis la
      Boîte de réception, une recherche trouve un message rangé dans « Archives », avec son dossier d'origine ; en
      « Dossier courant », il n'est plus trouvé. Clients : angular requis, mobile requis avec **divergence temporaire**
      (raison : « portée et tri arrivent sur le mobile avec la refonte mobile », tache : task-451). Implémenté dans
      weda2, vu rouge par mutation
- [ ] `data-testid` sur chaque élément interactif ajouté
- [ ] Mesure de coût consignée dans le `## Develop log` : p95 de la recherche « tous les dossiers » sur la boîte de
      11 178 messages, comparé à la recherche dans la Boîte de réception
- [ ] Aucune donnée de santé en clair dans les logs
- [ ] client-angular : code-only, aucun commit

## Manual Test Plan

1. Lancer le backend sur le corpus fictif : `cd Api/Mail/src/AppHost && dotnet run`, puis le seed de référence. Lancer
   weda2 : `cd Client/Angular/front && npm start`.
2. Ranger un message contenant `psoriasis` dans « Archives », en mettre un autre à la Corbeille.
3. Depuis la Boîte de réception, rechercher `psoriasis` : le sélecteur indique « Tous les dossiers » ; le message
   d'« Archives » est trouvé avec son dossier ; celui de la Corbeille ne l'est pas.
4. Passer en « Dossier courant » : le message d'« Archives » disparaît.
5. Rechercher `catherine bernard`, passer en « Les plus récents » : les messages sont du plus récent au plus ancien, les
   « Résultats proches » restent à part en bas ; « Voir plus » continue dans le même ordre.
6. Ouvrir la Corbeille, rechercher : le sélecteur indique « Dossier courant ».

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — ergonomie de la recherche
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : inchangées — verdict de l'opérateur MSSanté (règle 14) ; « tous les dossiers » désigne les
  dossiers de la boîte, jamais ceux d'une autre boîte de la personne
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : chaque recherche tracée (`MailSearch`) au nom de la personne réelle, avec son rôle et la portée,
  3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — base de la boîte, inchangée
- **AIPD / impact RGPD** : inchangé
