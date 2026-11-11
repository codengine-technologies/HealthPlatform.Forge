# todo-task-447.md — Recherche : tri des résultats (la portée reste le dossier sélectionné)

**Repos**: api-mail, dtos-mss, client-angular
**Dependencies**: done-task-445 (mode résultats)
**Epic**: E023
**Priorité**: EPIC E023, demandée par l'humain le 2026-11-10, **recadrée par l'humain le 2026-11-11**.

> **Décision humaine du 2026-11-11 : la recherche porte uniquement sur le dossier sélectionné.** La première version
> de cette task faisait chercher par défaut dans « Tous les dossiers », avec un sélecteur de portée. Cette partie est
> **retirée** : pas de sélecteur, pas de recherche dans toute la boîte. La règle RG-E022-05 (« une recherche dans un
> dossier ne rend que des messages de ce dossier ») reste la règle. Seul le **tri** est gardé.
>
> Le nom du fichier garde l'ancien titre (`…portee_tous_les_dossiers_et_tri`), que la convention fige à la création.

## Ce qui est établi

- La recherche porte sur le dossier courant (`folderPath`) ; RG-E022-05 est vérifiée en continu par task-438.
- Le serveur ordonne par pertinence : tous les mots, puis une partie des mots, puis la section des proches (task-439,
  task-440). Aucun tri par date n'est proposé.

## Objective

Le médecin choisit l'ordre des résultats de sa recherche, dans le dossier sélectionné.

Règles :
- **Portée** : le dossier sélectionné, toujours. Aucun sélecteur de portée ; RG-E022-05 inchangée.
- **Tri**, dans l'en-tête des résultats :
  - **« Pertinence »** (défaut) : l'ordre du serveur, par groupes puis proches ;
  - **« Les plus récents »** : les résultats exacts (tous les mots et une partie des mots, réunis) triés par date
    d'envoi décroissante, **par le serveur**, puis la partie « Résultats proches » à part, elle aussi par date.
  - Le tri est fait par le serveur sur l'ensemble des résultats du dossier, pas sur la page affichée ; « Voir plus »
    suit le tri.
- Le tri choisi est une étiquette du mode résultats (task-445) ; le changer relance la recherche.
- Le tri est rejoué par l'historique des recherches.
- **Règle 14 inchangée.**

### Hors périmètre

- La recherche dans plusieurs dossiers ou dans toute la boîte : **écartée par l'humain le 2026-11-11**.
- Le mobile : task-451.
- Les dossiers de recherche enregistrés : hors lot.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`, `HealthPlatform.Dtos.Mss.csproj`, weda2 (`nx build weda2`)
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`, `nx test weda2`, `nx test mss-lib`
- [ ] Tests unitaires : tri par pertinence inchangé, tri par date sur les exacts réunis puis les proches, valeur de tri
      absente = pertinence (≥ 1 test par branche)
- [ ] **Tests d'intégration de bout en bout (règle 1b), `POST /api/v1/Search/semantic`**, sur le corpus fictif, lus dans
      la réponse réelle (`Hits`, leur ordre et leur `FolderPath`), chacun vu rouge par mutation :
      - **les plus récents** : les exacts sont triés par date décroissante sur **l'ensemble** des résultats du dossier
        (le plus récent de la page 2 en mode pertinence est en page 1), puis les proches ; aucun proche n'est intercalé ;
      - **pertinence** : l'ordre d'aujourd'hui (tous les mots, une partie, proches) est inchangé, sans tri ou avec
        « Pertinence » ;
      - **dossier sélectionné** : avec l'un ou l'autre tri, aucun message d'un autre dossier n'est rendu (RG-E022-05) ;
      - **cas d'échec** : une valeur de tri inconnue → 400 en `ProblemDetails`
- [ ] Contrat `dtos-mss` publié (rétrocompatible : sans tri, le comportement d'aujourd'hui) et consommateurs .NET mis à
      jour ; types TypeScript de weda2 alignés
- [ ] Tests de composant weda2 : bascule de tri, étiquette de tri, relance de la recherche au changement de tri,
      « Voir plus » qui garde le tri ; chacun vu rouge par mutation
- [ ] **Scénario e2e** `E2E-SEARCH-011` v1 : « Trier les résultats du plus récent au plus ancien » — attendu : dans la
      Boîte de réception, une recherche passée en « Les plus récents » rend les messages exacts du plus récent au plus
      ancien, puis les proches à part ; aucun message d'un autre dossier. Clients : angular requis, mobile requis avec
      **divergence temporaire** (raison : « le tri arrive sur le mobile avec la refonte mobile », task : task-451).
      Implémenté dans weda2, vu rouge par mutation
- [ ] `data-testid` sur chaque élément interactif ajouté
- [ ] Mesure de coût consignée dans le `## Develop log` : p95 de la recherche « Les plus récents » dans la Boîte de
      réception de la boîte de 11 178 messages, comparé au tri par pertinence
- [ ] Aucune donnée de santé en clair dans les logs
- [ ] client-angular : code-only, aucun commit

## Manual Test Plan

1. Lancer le backend sur le corpus fictif : `cd Api/Mail/src/AppHost && dotnet run`, puis le seed de référence. Lancer
   weda2 : `cd Client/Angular/front && npm start`.
2. Ranger un message contenant `psoriasis` dans « Archives ».
3. Depuis la Boîte de réception, rechercher `psoriasis` : le message d'« Archives » n'est **pas** trouvé ; il l'est en
   ouvrant « Archives » puis en relançant la recherche.
4. Rechercher `catherine bernard`, passer en « Les plus récents » : les messages vont du plus récent au plus ancien,
   les « Résultats proches » restent à part en bas ; « Voir plus » continue dans le même ordre.
5. Repasser en « Pertinence » : l'ordre d'avant revient (tous les mots, puis une partie, puis les proches).
6. Rejouer la recherche depuis l'historique : le tri choisi revient.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — ergonomie de la recherche
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : inchangées — verdict de l'opérateur MSSanté (règle 14) ; la recherche ne lit que le dossier
  sélectionné de la boîte
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : chaque recherche tracée (`MailSearch`) au nom de la personne réelle, avec son rôle, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — base de la boîte, inchangée
- **AIPD / impact RGPD** : inchangé
