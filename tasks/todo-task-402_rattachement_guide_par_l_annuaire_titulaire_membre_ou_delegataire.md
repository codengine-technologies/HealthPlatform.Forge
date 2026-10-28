# todo-task-402 — Rattachement guidé par l'Annuaire Santé : titulaire, membre ou délégataire

**Repos**: dtos-mss, api-mail, client-mobile, client-angular
**Dependencies**: aucune
**Epic**: E020
**EpicTitle**: Boîte partagée : une base par boîte, tout acte imputé

> **Cadre** : CLAUDE.md règle 14, réécrite le 2026-10-28 (commit `ca0adaf`). Analyse d'origine :
> le nom de base `u_{rpps}_{slug}_{hash(adresse)}` donne au délégataire une **seconde base**, copie
> des données de santé du délégant. L'EPIC E020 passe à « une boîte = une base », l'accès ouvert par
> l'opérateur, tout acte imputé à son auteur réel. Cette task pose la **qualification du rôle** dont
> dépendent le verrou d'accès et le hors-ligne du titulaire (task-403).
>
> Ordre de l'EPIC : 402 (rattachement guidé) → 403 (accès subordonné à l'opérateur) → 404 (une base
> par boîte) → 405 (tout acte imputé) → 406 (mesure de charge d'une boîte partagée).
>
> **Aucune reprise** (humain, 2026-10-28) : rien n'est en production ; le registre et les bases
> praticien de dev sont supprimés au déploiement de l'EPIC. Tout rattachement naît qualifié.

## Ce qui est établi

- **Rattachement** : `POST /api/v1/account/mailboxes` → `MailboxManagementService.AttachAsync`
  (`Api/Mail/src/Application/Services/Mailboxes/MailboxManagementService.cs`). Ordre « sonder, puis
  persister » : sonde IMAP XOAUTH2 avec le jeton PSC, puis `ITenantRegistryClient.AttachMailboxAsync`.
- **Registre** : `mss_accounts` (rattachement compte × messagerie) porte `validated_by_psc_subject`
  et `validated_by_rpps` (NOT NULL), mais **aucun rôle**. Clé unique `(account_id, mailbox_address)` :
  deux comptes peuvent rattacher la même adresse.
- **Annuaire Santé** : api-mail interroge déjà l'API FHIR R4 **par RPPS**
  (`DirectorySearchEngine.cs:63`) et lit les adresses de `Practitioner.telecom` et
  `PractitionerRole.telecom` (`FhirBundleParser.cs:142`), avec une limite de débit
  (`AnnuaireSanteService.RequestsPerSecond`, `RedisAnnuaireQuotaGate`). Il **ne lit pas** le type de
  la BAL (personnelle / organisationnelle / applicative).
- **Clients** : écrans de rattachement `mailbox-onboarding` et `mailbox-management` (mobile, et weda2
  `features/mailbox-onboarding`, `features/mailbox-management`), formulaire partagé
  `attach-mailbox-form.component.ts` côté mobile.
- **Banc e2e** : aucun Annuaire dans le profil e2e. Dovecot accepte toute identité (`passdb static`).
  `E2eSeedPlan` n'a qu'une personne (le praticien e2e, deux boîtes).

## Décisions actées (humain, 2026-10-28)

1. Le rattachement se fait par **deux voies, et deux seulement** :
   - **« Mes boîtes »** : la liste des BAL que l'Annuaire Santé publie pour le RPPS du jeton PSC. Le PS
     **choisit**, il ne saisit pas ;
   - **« Ajouter une BAL déléguée »** : saisie libre, **réservée à la délégation**. Elle n'ouvre jamais
     le rôle de titulaire.
2. Une adresse organisationnelle n'a pas de titulaire : ses PS sont **membres**.
3. Une BAL personnelle en **liste rouge** n'est rattachable qu'en délégation : conséquence assumée.
4. Une boîte **« à requalifier »** garde l'accès en ligne avec les droits d'un délégataire (pas de
   hors-ligne), avec un bandeau « rattachez-la de nouveau depuis Mes boîtes ».

## Objective

Après sa connexion PSC, le PS rattache une messagerie soit en la **choisissant** dans la liste que
l'Annuaire Santé publie pour son RPPS, soit en **saisissant** l'adresse d'une BAL qui lui est
déléguée. Chaque rattachement porte un **rôle** — titulaire, membre ou délégataire — calculé par le
serveur, jamais déclaré par le client. Cette task **ne change aucun accès** : elle pose la
qualification que la task-403 (verrou, hors-ligne du titulaire) et la task-406 (résorption)
utilisent.

## Règles

1. **La liste vient du serveur.** Le RPPS est celui de la **session PSC**, jamais une valeur du client.
   Pour chaque BAL : l'adresse, le type (personnelle ou organisationnelle, lu dans les métadonnées
   MSSanté de l'Annuaire) et l'indicateur « déjà rattachée ». Les BAL **applicatives** ne sont pas
   proposées.
2. **Le rôle est fixé par le serveur, au rattachement.**
   - **« Mes boîtes »** : le serveur **revérifie** que l'adresse est dans la liste du RPPS de la
     session. BAL personnelle → **titulaire** ; BAL organisationnelle → **membre**. Une adresse
     absente de la liste est refusée.
   - **Saisie libre** : une adresse qui figure dans la liste du PS est **refusée** (« choisissez-la
     dans Mes boîtes »). Sinon → **délégataire**.
   - Dans les deux cas : **sonder, puis persister**. Rien n'est écrit sans sonde IMAP réussie avec
     le jeton PSC de la personne.
3. **Annuaire indisponible** : « Mes boîtes » rend une erreur `application/problem+json` 503 et
   l'écran affiche « Annuaire Santé momentanément indisponible, réessayez ». La saisie libre reste
   ouverte, **pour la délégation seulement** — elle ne remplace jamais la liste.
4. **Requalification à chaque ré-authentification** : le rôle est recalculé contre l'Annuaire.
   - Un titulaire ou un membre dont l'adresse n'est plus publiée pour son RPPS passe **« à
     requalifier »**. Il ne devient **jamais délégataire automatiquement**.
   - « À requalifier » : accès en ligne inchangé, droits d'un délégataire (pas de hors-ligne une fois
     la task-403 livrée), bandeau « rattachez-la de nouveau depuis Mes boîtes ».
   - Annuaire injoignable à ce moment : le rôle enregistré est **gardé**.
5. **Aucun rattachement existant à reprendre** : le registre de dev repart vide. Le rôle est
   **obligatoire** sur tout rattachement (contrainte NOT NULL), il n'existe pas d'état « non qualifié ».
6. **Weda désigne une adresse** (E2E-WEDA-001) : présente dans « Mes boîtes » → présélectionnée ;
   sinon → formulaire de délégation pré-rempli.
7. **Liste rouge** : aucun contournement proposé à l'écran (décision 3).
8. **Traces (règle 14)** : `MailboxAttached`, `MailboxAttachRefused` et la requalification portent le
   **rôle**, le **RPPS de la personne qui agit** et le motif de refus. La consultation de l'Annuaire
   n'est pas tracée au journal : elle ne touche aucune donnée de santé.

## Definition of Done

- [ ] Build passes (0 errors) sur `dtos-mss`, `api-mail`, `client-mobile`, `client-angular` (code-only)
- [ ] Tests pass (0 failures) sur chaque repo listé
- [ ] Contrat `dtos-mss` : rôle et type d'adresse sur la boîte rattachée, DTO « BAL proposée », mode
      de rattachement dans la requête — package publié, consommateurs .NET bumpés, types TypeScript
      mobile et Angular régénérés
- [ ] Registre : migration (rôle et type d'adresse sur le rattachement), auditée (règle 7c : fichier
      relu, aucune opération fantôme, aucune dérive)
- [ ] Unit tests du parseur FHIR : type de BAL personnelle, organisationnelle, applicative écartée,
      métadonnée absente
- [ ] Unit tests du calcul de rôle : chaque branche des règles 2 et 4
- [ ] Test d'intégration de bout en bout pour la lecture de « Mes boîtes » : liste du RPPS de la
      session lue dans la réponse réelle (type et « déjà rattachée »), 503 problem+json si l'Annuaire
      est indisponible, refus sans session PSC — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout pour `POST /account/mailboxes` via « Mes boîtes » : rôle
      `titulaire` lu dans la réponse et dans `GET /account/mailboxes` ; adresse hors liste refusée et
      rien de persisté — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : BAL organisationnelle → rôle `membre` lu dans la réponse —
      vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout pour la saisie libre : rôle `délégataire` ; l'adresse de la
      propre liste du PS refusée avec son code, rien de persisté — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout pour `POST /account/mailboxes/{id}/reauthenticate` : titulaire
      dont l'adresse a quitté l'Annuaire → état « à requalifier » lu dans la réponse ; Annuaire
      injoignable → rôle gardé — vu rouge (règle 1b)
- [ ] Test d'intégration : rôle et RPPS de la personne qui agit lus dans le journal d'audit réel
      (rattachement, refus, requalification) — vu rouge (règle 1b)
- [ ] Mobile et weda2 : écran de rattachement à deux voies, badge de rôle sur chaque boîte, bandeau
      « à requalifier », `data-testid` sur tous les éléments interactifs
- [ ] UI component tests : écran à deux voies (rendu + choix dans la liste + saisie libre refusée),
      badge de rôle
- [ ] **Banc e2e** : un Annuaire FHIR simulé dans le profil e2e publie, pour le RPPS e2e,
      `boite-praticien` (personnelle) et `boite-secondaire` (organisationnelle) ; une seconde
      identité PSC « délégataire e2e » est au seed ; `E2eSeed` enregistre les rôles
- [ ] Scénario E2E-MAILBOX-003 (v1, rattachement via « Mes boîtes », badges titulaire et membre)
      ajouté dans Api/Mail/e2e/scenarios.yml, et implémenté dans chaque client où il est requis
      (mobile, angular)
- [ ] Scénario E2E-MAILBOX-004 (v1, délégation par saisie libre, refus de sa propre adresse) ajouté
      dans Api/Mail/e2e/scenarios.yml, et implémenté dans chaque client où il est requis (mobile,
      angular)
- [ ] Scénario E2E-WEDA-001 versionné (v2 : adresse désignée par Weda présélectionnée ou pré-remplie)
      dans Api/Mail/e2e/scenarios.yml, et implémenté dans chaque client où il est requis (angular ;
      mobile non applicable — l'application mobile n'est pas embarquée dans Weda)
- [ ] Aucune donnée de santé en clair dans les logs ; aucun RPPS ni adresse complète en clair
      (adresses masquées)
- [ ] Évènements PGSSI-S journalisés : rattachement, refus de rattachement, requalification — avec
      la personne, le rôle et la boîte
- [ ] Authentification PS via PSC testée bout-en-bout (sonde XOAUTH2 avant toute écriture)
- [ ] AIPD mise à jour (nouvelle source : Annuaire Santé ; rôle de délégataire)

## Manual Test Plan

- Backend e2e : `cd Api/Mail && dotnet run --project src/AppHost` (profil `e2e`)
- Mobile : `cd Client/Mobile && npm start` → http://localhost:4200
- weda2 : via le faux hôte du profil e2e (cf. `agents/e2e.md`)
- Se connecter avec l'identité PSC e2e. Écran de rattachement : « Mes boîtes » liste les deux BAL.
  - Choisir la BAL personnelle → badge **Titulaire**.
  - Choisir la BAL organisationnelle → badge **Membre**.
- « Ajouter une BAL déléguée » : saisir l'adresse personnelle → refus « choisissez-la dans Mes
  boîtes », aucune boîte ajoutée.
- Se connecter avec l'identité « délégataire e2e », saisir l'adresse de `boite-praticien` → badge
  **Délégation**.
- Arrêter l'Annuaire simulé → « Mes boîtes » affiche l'indisponibilité et « Réessayer » ; la saisie
  libre reste disponible.
- Retirer `boite-praticien` de l'Annuaire simulé, puis ré-authentifier la boîte → bandeau « à
  requalifier », la messagerie reste lisible en ligne.
- Écran Audit de weda2 : les rattachements portent le rôle et le RPPS de la personne.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — qualification de rattachement, sans exigence DSR publiée
- **Exigences DSR honorées** : non applicable — aucune exigence DSR ne porte sur le rôle d'un
  rattachement de BAL
- **INS** : non applicable — aucun patient n'est manipulé
- **Authentification PS** : PSC / e-CPS, eIDAS substantiel. Le RPPS vient du jeton PSC ; l'accès est
  validé par XOAUTH2 auprès de l'opérateur MSSanté avant toute écriture
- **Habilitations** : rôle issu de l'Annuaire Santé (titulaire, membre) ou de la délégation (saisie
  libre validée par l'opérateur). Le client ne déclare jamais son rôle
- **Interop CI-SIS** : API FHIR R4 de l'Annuaire Santé (Practitioner, PractitionerRole, métadonnées
  MSSanté de `telecom`)
- **Tracé PGSSI-S** : rattachement, refus de rattachement, requalification — personne (RPPS, nom),
  rôle, boîte. Conservation selon la famille de trace en vigueur, inchangée
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — le registre ne reçoit aucune donnée de santé
- **AIPD / impact RGPD** : à mettre à jour — nouvelle source (Annuaire Santé, données publiques des
  PS), rôle de délégataire ; la mention « accès au nom d'un délégant » suspendue par task-401 est à
  reprendre

## Branches

- `dtos-mss` (lazy) : aucune branche au /start — `/develop` la crée au premier contrat touché
- `client-angular` (code-only) : la forge écrit sur la branche courante de `Client/Angular/` ;
  l'humain gère branche, commit, push et PR TFS
