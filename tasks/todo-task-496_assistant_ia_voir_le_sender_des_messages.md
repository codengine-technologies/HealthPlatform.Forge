# todo-task-496 — Assistant IA : voir qui a écrit pour le compte de la boîte

**Repos**: api-mcp
**Dependencies**: aucune
**Epic**: E026

> **Cadre** : *MSSanté – Guide d'implémentation de la délégation de BAL via API LPS*, ANS, **v1.0 du
> 26/11/2026** (`Docs/Referentiel/MSSANTE/MSSanté - Guide d'implémentation de la délégation de BAL v1.0.pdf`),
> §3.3, exigence **ECO.1.2.10** : un message reçu porteur d'un `Sender` doit être présenté comme envoyé par le
> délégataire pour le compte du délégant.
>
> **Origine** : audit de conformité du 2026-11-26 contre ce guide (écart 4). Le médecin lit sa messagerie depuis
> un assistant IA par le serveur MCP (E026). L'assistant ne reçoit que le `From`, présenté comme « expéditeur ».
> Il attribue donc au titulaire un message écrit par son délégataire.
>
> **Single repo justifié** : api-mail rend déjà le `Sender` sur la route que lit api-mcp ; aucun client graphique
> n'est concerné (l'écran de lecture, la conversation et l'aperçu relèvent de task-407 et task-495).

## Ce qui est établi

- **Outils concernés** : `list_messages` et `search_messages` (`Tools/MailTools.cs:43-72`). Leur description dit
  « expéditeur » et leur vue `MessageHeaderView` (`Tools/ToolViews.cs:17-28`) ne porte que `FromName`,
  `FromAddress`.
- **Contrat local** : `ApiMailHeader` (`ApiMail/ApiMailContracts.cs:30-41`) ne déclare que `From`.
- **api-mail rend déjà le `Sender`** sur `GET api/v1/Mail/folders/{dossier}/emails/{uids}` : la route rend des
  `MailDto`, dont le `Sender` (nom, adresse) est renseigné à la lecture depuis la base
  (`MailRepository.cs:2634, 3753, 5391`) et à l'ingestion IMAP (`EmailBuildingService.cs:161`). Il est vide quand
  l'en-tête est absent ou égal au `From` (`EmailAddressHelper.ExtractSenderAddress`). **À confirmer par
  `/develop` sur la route exacte** ; s'il manquait, c'est une question (`questions/task-496.md`), pas un
  élargissement silencieux à api-mail.
- **task-479** (au backlog) ajoute la lecture d'un message par l'assistant. Elle ne parle pas du `Sender`.

## Objective

Quand l'assistant IA liste ou retrouve un message écrit par un délégataire pour le compte d'une boîte, il sait
qui l'a écrit et pour quelle boîte, et peut le dire au médecin.

## Règles

1. **Chaque en-tête de message rendu à l'assistant** porte, en plus du `From` (la boîte), le **nom et l'adresse
   du `Sender`** quand il existe ; sinon ces champs sont vides.
2. **La description des outils le dit** : « From = la boîte qui envoie ; Sender = la personne qui a écrit pour
   son compte (délégataire), absent quand la boîte a écrit elle-même ».
3. **Toute vue d'en-tête de l'assistant suit la règle**. Si task-479 est livrée avant celle-ci, son outil de
   lecture y entre aussi ; sinon, task-479 la reprend.
4. **Garde-fous inchangés** : jamais de RPPS (le `Sender` n'en porte pas), jamais de contenu de message dans
   `list_messages` ni `search_messages`.
5. **Règle 14** : aucun acte nouveau. La lecture d'en-têtes et la recherche sont déjà tracées au nom du médecin.

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mcp`
- [ ] Tests pass (0 failures) sur `api-mcp`
- [ ] Unit tests de la vue d'en-tête : avec `Sender` → nom et adresse rendus ; sans `Sender` → champs vides
- [ ] Test d'intégration de bout en bout pour l'outil `list_messages` (vraie pile HTTP MCP, api-mail simulé comme
      fournisseur externe) : un en-tête dont api-mail rend un `Sender` le rend à l'assistant (nom et adresse lus
      dans la réponse réelle de l'outil) ; un en-tête sans `Sender` rend les champs vides — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout pour l'outil `search_messages` : même comportement sur un résultat de
      recherche — vu rouge (règle 1b)
- [ ] Description des outils `list_messages` et `search_messages` mise à jour (règle 2), lue dans la liste des
      outils exposée par le serveur
- [ ] `python Tools/contracts/contract_impact.py surface --consumer api-mcp` montre le `Sender` dans la surface
      lue ; `check` sans erreur d'outil
- [ ] Aucune donnée de santé en clair dans les logs ; aucun RPPS rendu à l'assistant
- [ ] Pas de scénario e2e : api-mcp n'a pas de voie e2e, son filet est le test d'intégration (CLAUDE.md, section
      api-mcp)

## Manual Test Plan

- Lancer api-mail (profil `e2e`, `cd Api/Mail && dotnet run --project src/AppHost`) puis api-mcp
  (`cd Api/Mcp && dotnet run --project src/HealthPlatform.Api.Mcp`), et brancher un client MCP (Claude Desktop ou
  MCP Inspector) sur api-mcp ; se connecter en e-CPS.
- Prérequis : dans `boite-praticien`, un message écrit par le délégataire pour le compte de la boîte (parcours
  E2E-SHARED-002).
- Demander à l'assistant « liste les derniers messages de ma boîte » : pour ce message, il indique l'expéditeur
  (la boîte) et la personne qui l'a écrit pour son compte.
- Demander « cherche le message envoyé par {nom du délégataire} » : le résultat porte la même information.
- Un message ordinaire n'a aucune mention de délégataire.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — exigence du guide ANS de délégation de BAL, non encore intégré aux référentiels
- **Exigences DSR honorées** : guide ANS de délégation de BAL v1.0 (26/11/2026), **ECO.1.2.10**
- **INS** : non applicable — en-têtes de messages seulement, aucune donnée patient ajoutée
- **Authentification PS** : PSC / e-CPS via psc-auth-proxy, inchangée ; le jeton remis au client IA ne vaut que
  pour api-mcp
- **Habilitations** : inchangées ; l'accès aux en-têtes d'une boîte reste soumis au verdict de l'opérateur
  (task-403), appliqué par api-mail
- **Interop CI-SIS** : non applicable ; en-têtes MSSanté RFC 5322 (`From`, `Sender`) déjà lus par api-mail
- **MSSanté** : BAL personnelle ou organisationnelle déléguée ; `Sender` posé par le logiciel du délégataire
- **Tracé PGSSI-S** : aucun évènement nouveau ; liste et recherche déjà tracées au nom du médecin (E026).
  Conservation inchangée
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : à vérifier — le nom et l'adresse du délégataire, déjà visibles dans la messagerie,
  sont désormais transmis au client IA du médecin, comme le `From` l'est déjà ; à mentionner dans la section
  « assistant IA » de l'AIPD si elle énumère les champs transmis

## Timings

*(généré par `tools/timing/report.sh --task task-496 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| / | en cours | — | — | — | — | — |
| /start | skipped | 32 s | — | — | — | lancé par erreur (/start 496), interrompu par l'humain avant tout pré-flight ; aucune branche créée |
| **Total cycle** | | **32 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
