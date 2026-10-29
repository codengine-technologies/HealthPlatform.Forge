# todo-task-407 — Le délégataire écrit pour le compte du délégant

**Repos**: dtos-mss, api-mail, client-mobile, client-angular
**Dependencies**: task-404 (l'identité d'expéditeur appartient à la boîte), task-405 (le nom et le prénom PSC de la personne qui agit)
**Epic**: E020

> **Cadre** : référentiel socle MSSanté #2 de l'ANS, *Clients de messageries sécurisées de santé*,
> extrait draft v1.1.0 sur la délégation
> (`Docs/Referentiel/MSSANTE/ANS_MSS_Ref2_Clients_de_messageries_MSSanté_v1.1.0_extrait_draft_delegation.pdf`),
> exigences **ECO.1.2.9**, **ECO.1.2.10** et **ECO.1.2.11**. Analyse de conformité du 2026-10-29 :
> l'EPIC E020 (task-402 à 406) couvre ECO.1.2.8 (connexion à la BAL déléguée avec le jeton PSC du
> délégataire) et ECO.1.2.11, mais aucune task ne pose ni n'affiche l'en-tête `Sender`.
>
> **Draft** : l'ANS a annoté ECO.1.2.9 en marge (format `no-reply-…` réservé aux secrétaires ?
> partie fixe et partie variable ?). La règle est implémentée telle qu'écrite, et le calcul de
> l'adresse du `Sender` vit à **un seul endroit**, pour suivre la version finale.

## Ce qui est établi

- **Connexion (ECO.1.2.8, conforme)** : IMAP et SMTP s'authentifient en XOAUTH2 avec l'adresse de la
  boîte choisie (`userContextInfo.Email`) et le jeton PSC de la personne
  (`ImapConnectionService.cs:378`, `SmtpConnectionFactory.cs:371`).
- **Envoi** : `SmtpService.SetMessageRecipients` (`SmtpService.cs:299`) ne pose que le `From`, avec
  l'adresse envoyée par le client. Le nom affiché vient de `ResolveSenderDisplayNameAsync`
  (`:272`), qui lit l'identité d'expéditeur (`SenderIdentityDto`) dans les **réglages de la
  personne**. Aucun en-tête `Sender`.
  - Un délégataire enverrait donc aujourd'hui `From: <son propre nom> <adresse du délégant>` : c'est
    l'inverse de ECO.1.2.9.
  - **Piège MailKit** : `SmtpClient.SendAsync(MimeMessage)` prend le `Sender` comme `MAIL FROM`
    quand il est présent. Or l'ANS exige que `MAIL FROM` soit la **BAL déléguée**.
- **Autres messages émis** : accusé de lecture (`MdnService.cs:235`), brouillons (`DraftMimeBuilder.cs:21`).
- **Réception** : `MailDto` n'a pas de champ `Sender`. Dans une enveloppe IMAP, le `Sender` est
  **recopié du `From`** quand l'en-tête est absent.
- **Réponse (ECO.1.2.11, conforme)** : mobile et weda2 répondent au `Reply-To` s'il existe, sinon au
  `From` (`reply-all-recipients.util.ts`), jamais au `Sender`.
- **BAL propre du délégataire** : la liste des BAL publiées par l'Annuaire Santé pour un RPPS existe
  depuis la task-402 (« Mes boîtes »).

## Décisions actées (humain, 2026-10-29)

1. **Le nom du `From` est l'identité d'expéditeur de la boîte**, donnée de la boîte (task-404, règle
   amendée), jamais le nom du délégataire.
2. **Le `Sender` est posé pour le délégataire et pour une boîte « à requalifier »** (droits d'un
   délégataire). Le **titulaire** et le **membre** d'une adresse organisationnelle (co-titulaire,
   publié par l'Annuaire) n'en posent pas.
3. **Adresse du `Sender`** :
   - la **BAL personnelle** publiée par l'Annuaire Santé pour le RPPS du délégataire, **si elle est
     chez le même opérateur** que la BAL déléguée — reconnu au **domaine** de l'adresse, comme dans
     les exemples de l'ANS ;
   - sinon `no-reply-<prénom.nom>@<domaine de la BAL déléguée>`.

## Objective

Quand un délégataire écrit depuis la boîte de son délégant, le destinataire **sait** que le message
a été envoyé par le délégataire **pour le compte** du titulaire de la boîte, et il répond à la
boîte. Quand un médecin reçoit un tel message, l'écran le lui dit.

## Règles

1. **À l'envoi, pour un délégataire ou une boîte « à requalifier »** :
   - `From` : identité d'expéditeur de la boîte, adresse de la BAL déléguée ;
   - `Sender` : « Prénom Nom » du délégataire (identité PSC, task-405), adresse selon la décision 3 ;
   - enveloppe SMTP `MAIL FROM` : **toujours la BAL déléguée**, jamais l'adresse du `Sender`.
2. **Le serveur calcule tout.** Le rôle, le nom et l'adresse du `Sender` ne viennent jamais du
   client. Une adresse `From` différente de la boîte de la session est refusée (problem+json 400),
   rien n'est envoyé.
3. **Partie `prénom.nom`** de l'adresse `no-reply-…` : minuscules, sans accents, espaces et
   apostrophes remplacés par des tirets, prénom et nom séparés par un point.
4. **Nom ou prénom PSC indisponibles** : l'envoi est **refusé** (problem+json, « identité du
   délégataire indisponible, reconnectez-vous avec Pro Santé Connect »), rien n'est envoyé. Jamais
   de RPPS dans un en-tête (garde-fou métier).
5. **Tous les messages émis depuis la boîte** suivent la règle 1 : nouveau message, réponse, réponse
   à tous, transfert, accusé de lecture, envoi différé exécuté plus tard (avec l'identité de la
   personne qui l'a demandé). Un brouillon ne porte pas de `Sender` : il est calculé **à l'envoi**,
   pour la personne qui envoie.
6. **À la réception** : `MailDto` porte le `Sender` (nom et adresse) **seulement** si l'en-tête est
   présent **et** différent du `From`. Dans la lecture d'un message, mobile et weda2 affichent
   « Envoyé par {nom du Sender} pour le compte de {nom du From} ». La liste des messages garde le
   `From`.
7. **Répondre (ECO.1.2.11)** : la réponse va au `Reply-To`, sinon au `From` ; la réponse à tous
   n'ajoute **jamais** l'adresse du `Sender`. Comportement actuel, verrouillé par des tests.
8. **Traces (règle 14)** : l'envoi reste imputé à la personne réelle (task-405). La trace d'envoi
   indique qu'il a été fait **pour le compte** de la boîte.

## Definition of Done

- [ ] Build passes (0 errors) sur `dtos-mss`, `api-mail`, `client-mobile`, `client-angular` (code-only)
- [ ] Tests pass (0 failures) sur chaque repo listé
- [ ] Contrat `dtos-mss` : `Sender` (nom, adresse) sur `MailDto` — package publié, consommateurs .NET
      bumpés, types TypeScript mobile et Angular régénérés
- [ ] Unit tests du calcul du `Sender` : chaque rôle (titulaire, membre, délégataire, à requalifier)
      croisé avec la BAL propre (même domaine, autre domaine, aucune), et le nom indisponible
- [ ] Unit tests de la partie `prénom.nom` (accents, espaces, apostrophes, noms composés)
- [ ] Test d'intégration de bout en bout pour l'envoi par un délégataire : le message **reçu** par le
      destinataire porte `From` = identité et adresse de la boîte, `Sender` = nom du délégataire et
      `no-reply-…@{domaine}`, et l'enveloppe `MAIL FROM` est la BAL déléguée (lue dans le message
      reçu, `Return-Path`) — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : délégataire ayant sa BAL personnelle chez le même
      opérateur → `Sender` = sa BAL ; chez un autre opérateur → `no-reply-…` — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : titulaire et membre → message reçu **sans** `Sender` — vu
      rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : `From` différent de la boîte de la session → 400
      problem+json, rien de reçu ; nom PSC indisponible → refus problem+json, rien de reçu — vu rouge
      (règle 1b)
- [ ] Test d'intégration de bout en bout : accusé de lecture et réponse émis par un délégataire
      portent le `Sender` — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout pour la lecture d'un message : `Sender` présent et différent
      du `From` → lu dans `MailDto` ; absent, ou égal au `From` → vide — vu rouge (règle 1b)
- [ ] Mobile et weda2 : mention « Envoyé par … pour le compte de … » dans la lecture d'un message ;
      `data-testid` sur la mention
- [ ] UI component tests : mention affichée seulement avec un `Sender` ; « Répondre » et « Répondre
      à tous » visent le `From` (ou le `Reply-To`), jamais le `Sender`
- [ ] Scénario E2E-SHARED-002 (v1 : le délégataire écrit depuis la boîte du titulaire ; le
      destinataire lit « Envoyé par {délégataire} pour le compte de {titulaire} », et sa réponse
      arrive dans la boîte du titulaire) ajouté dans Api/Mail/e2e/scenarios.yml, et implémenté dans
      chaque client où il est requis (mobile, angular)
- [ ] Aucune donnée de santé en clair dans les logs (INS, NIR, contenu CDA, contenu MSSanté) ; aucun
      RPPS dans un en-tête de message
- [ ] Évènements PGSSI-S journalisés : envoi « pour le compte de » la boîte, imputé à la personne
      réelle ; refus d'envoi (identité indisponible, `From` étranger à la boîte)

## Manual Test Plan

- Backend e2e : `cd Api/Mail && dotnet run --project src/AppHost` (profil `e2e`) ; mobile
  `cd Client/Mobile && npm start` ; weda2 via le faux hôte.
- Titulaire e2e et délégataire e2e sur `boite-praticien` (seconde personne du seed, task-404).
- Le titulaire règle l'identité d'expéditeur de la boîte (« Dr Prénom Nom »).
- Le délégataire écrit un message à la seconde boîte e2e. Dans la seconde boîte : « Envoyé par
  {Prénom Nom du délégataire} pour le compte de Dr Prénom Nom » ; ouvrir la source du message :
  `From` = boîte du titulaire, `Sender` = `no-reply-prenom.nom@…`.
- Répondre depuis la seconde boîte : la réponse arrive dans la boîte du titulaire, pas chez le
  délégataire.
- Le titulaire écrit à son tour : aucune mention, aucun `Sender`.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur
- **Exigences DSR honorées** : référentiel socle MSSanté #2 (clients), ECO.1.2.9, ECO.1.2.10 et
  ECO.1.2.11 — version draft 1.1.0, à revérifier sur la version finale
- **INS** : non applicable — aucune donnée patient manipulée
- **Authentification PS** : PSC / e-CPS ; le nom du `Sender` vient de l'identité PSC (task-405)
- **Habilitations** : le rôle du rattachement (task-402) décide du `Sender` ; titulaire seulement par
  la liste de l'Annuaire Santé
- **Interop CI-SIS** : non applicable ; en-têtes MSSanté RFC 5321 (`MAIL FROM`) et RFC 5322
  (`From`, `Sender`)
- **MSSanté** : BAL personnelle ou organisationnelle déléguée ; BAL propre du délégataire lue dans
  l'Annuaire Santé ; adresse `no-reply-…` sur le domaine de l'opérateur de la BAL déléguée
- **Tracé PGSSI-S** : envoi pour le compte de la boîte imputé à la personne réelle ; refus d'envoi.
  Conservation inchangée (3 653 jours pour `HealthDataAccess`)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : à compléter — le nom du délégataire, et le cas échéant l'adresse de sa
  BAL personnelle, sont communiqués aux destinataires (exigence ANS ECO.1.2.9)
