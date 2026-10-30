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

- [x] Build passes (0 errors) sur `dtos-mss`, `api-mail`, `client-mobile`, `client-angular` (code-only)
- [x] Tests pass (0 failures) sur chaque repo listé
- [x] Contrat `dtos-mss` : `Sender` (nom, adresse) sur `MailDto` — package publié, consommateurs .NET
      bumpés, types TypeScript mobile et Angular régénérés
- [x] Unit tests du calcul du `Sender` : chaque rôle (titulaire, membre, délégataire, à requalifier)
      croisé avec la BAL propre (même domaine, autre domaine, aucune), et le nom indisponible
- [x] Unit tests de la partie `prénom.nom` (accents, espaces, apostrophes, noms composés)
- [x] Test d'intégration de bout en bout pour l'envoi par un délégataire : le message **reçu** par le
      destinataire porte `From` = identité et adresse de la boîte, `Sender` = nom du délégataire et
      `no-reply-…@{domaine}`, et l'enveloppe `MAIL FROM` est la BAL déléguée (lue dans le message
      reçu, `Return-Path`) — vu rouge (règle 1b)
- [x] Test d'intégration de bout en bout : délégataire ayant sa BAL personnelle chez le même
      opérateur → `Sender` = sa BAL ; chez un autre opérateur → `no-reply-…` — vu rouge (règle 1b)
- [x] Test d'intégration de bout en bout : titulaire et membre → message reçu **sans** `Sender` — vu
      rouge (règle 1b)
- [x] Test d'intégration de bout en bout : `From` différent de la boîte de la session → 400
      problem+json, rien de reçu ; nom PSC indisponible → refus problem+json, rien de reçu — vu rouge
      (règle 1b)
- [x] Test d'intégration de bout en bout : accusé de lecture et réponse émis par un délégataire
      portent le `Sender` — vu rouge (règle 1b)
- [x] Test d'intégration de bout en bout pour la lecture d'un message : `Sender` présent et différent
      du `From` → lu dans `MailDto` ; absent, ou égal au `From` → vide — vu rouge (règle 1b)
- [x] Mobile et weda2 : mention « Envoyé par … pour le compte de … » dans la lecture d'un message ;
      `data-testid` sur la mention
- [x] UI component tests : mention affichée seulement avec un `Sender` ; « Répondre » et « Répondre
      à tous » visent le `From` (ou le `Reply-To`), jamais le `Sender`
- [x] Scénario E2E-SHARED-002 (v1 : le délégataire écrit depuis la boîte du titulaire ; le
      destinataire lit « Envoyé par {délégataire} pour le compte de {titulaire} », et sa réponse
      arrive dans la boîte du titulaire) ajouté dans Api/Mail/e2e/scenarios.yml, et implémenté dans
      chaque client où il est requis (mobile, angular)
- [x] Aucune donnée de santé en clair dans les logs (INS, NIR, contenu CDA, contenu MSSanté) ; aucun
      RPPS dans un en-tête de message
- [x] Évènements PGSSI-S journalisés : envoi « pour le compte de » la boîte, imputé à la personne
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

## Branches

- `dtos-mss` (pushed, branche paresseuse) : feat/task-407-le-delegataire-ecrit-pour-le-compte-du — créée par `/develop` (contrat `MailDto.Sender`), publiée en 571.0.0
- `api-mail` (pushed) : feat/task-407-le-delegataire-ecrit-pour-le-compte-du — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-407-le-delegataire-ecrit-pour-le-compte-du
- `client-mobile` (pushed) : feat/task-407-le-delegataire-ecrit-pour-le-compte-du — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-407-le-delegataire-ecrit-pour-le-compte-du
- `client-angular` (code-only) : branche checkout au /start : `feature/nova-mss-weda-integration` — humain gère branche, commit, push, PR TFS

## Develop log

**Ordre** : `dtos-mss` → `api-mail` → `client-mobile` + `client-angular` (code-only).

| Repo | Commit | Build | Tests |
|---|---|---|---|
| `dtos-mss` | `e9de477` — `MailDto.Sender` ; CI run 571 → **HealthPlatform.Dtos.Mss 571.0.0** | ✅ | n/a |
| `api-mail` | `b1f522a9` (bump 561.0.0 → 571.0.0 inclus) | ✅ 0 erreur | ✅ domain 202, infrastructure 699, application 3927, api 1306, integration 1093 + 11 (task-407) |
| `client-mobile` | `858c7a5` | ✅ | ✅ Karma 1379/1379 |
| `client-angular` | non commité (code-only) | ✅ weda2 | ✅ Vitest 1405/1405 |

**Backend (api-mail)**
- `OnBehalfSenderResolver` / `OnBehalfSenderPolicy` (`Services/Mailboxes/OnBehalfSender.cs`) : le seul endroit des
  règles du `Sender`. Le référentiel est en draft : la version finale ne changera que cette classe.
- `SmtpService`, point d'étranglement de tous les envois (direct, brouillon, réponse, transfert, confirmé
  après mise de côté) : résolution avant toute connexion, `Sender` posé, enveloppe explicite
  `MAIL FROM` = la boîte, `RCPT TO` = To+Cc+Bcc. Le refus est tracé, puis levé (400 problem+json).
- `MdnService` : même règle. Le `From` de l'accusé porte l'identité d'expéditeur de la boîte (task-404).
- Réception : `EmailAddressHelper.ExtractSenderAddress` lit le `Sender` de l'enveloppe IMAP. Il est rendu `null`
  quand il est absent ou égal au `From`. Persisté dans `Mails.SenderAddress` / `SenderName`, migration
  `20261029140000_AddMailSenderColumns`, relu dans les 4 projections `MailDto`.
- Audit de migration (règle 7c) : deux colonnes `varchar(256)` nullables, aucune opération fantôme,
  aucune reprise. Le modèle EF (`HasMaxLength(256)`) dit la même chose : EnsureCreated et la migration
  passent tous deux les tests.
- Fixtures d'intégration : l'Annuaire Santé est un fournisseur externe, scripté par RPPS
  (`UseCaseFixture.Directory`, vide par défaut). Quatre harnais qui composent eux-mêmes
  `SmtpService` ont été adaptés :
  - `PendingSendConfirmation` : résolveur neutre, car son sujet est le classement des échecs ;
  - `MailServerTokenRefusal` : sa propre BAL, rattachée en titulaire et non plus en délégation par
    défaut, qui exigerait désormais un nom PSC ;
  - `SendMailOppositionGuard` : vrai résolveur ;
  - `ImapServicesFixture` : annuaire vide.

**Règle 1b — comportement → test d'intégration → preuve rouge** (`UseCases/OnBehalfSendEndToEndTests`, vraie
pile HTTP → `OutgoingMailService` → `SmtpService` → GreenMail ; Dovecot + base praticien pour la lecture) :

| Comportement | Test | Mutation vue rouge |
|---|---|---|
| Délégataire sans BAL sur le domaine : From = boîte, Sender = `no-reply-…`, Return-Path = boîte, trace OnBehalfOf imputée au délégataire | `ADelegateWithoutAPersonalMailboxOnTheDomain_…` | M1 (Sender non posé), M2 (enveloppe par défaut : MAIL FROM = Sender) |
| BAL personnelle même domaine → Sender = elle (ORG et autre domaine écartés) | `ADelegateWhosePersonalMailboxIsOnTheSameDomain_…` | M1, M2, M6 (BAL propre ignorée) |
| BAL personnelle sur un autre domaine → `no-reply-anne-marie.d-arc@…` | `…OnlyOnAnotherDomain_…` | M1 |
| Réponse depuis un brouillon (In-Reply-To) | `ADelegateReplyFromADraft_CarriesTheSender` | M1, M2 |
| Envoi mis de côté sans la carte puis confirmé | `ADelegateSendSetAsideWithoutTheCard_ThenConfirmed_…` | M1 |
| Titulaire et membre : aucun Sender | `TheHolderAndAMember_SendWithoutASender` ×2 | M5 (Sender pour tous les rôles) |
| From ≠ boîte → 400 `MAIL_FROM_NOT_MAILBOX`, rien reçu, refus tracé | `AFromThatIsNotTheMailbox_…` | M3 (contrôle retiré), M11 (refus non tracé) |
| Nom PSC absent → 400 `DELEGATE_IDENTITY_UNAVAILABLE`, rien reçu, refus tracé | `ADelegateWithoutAPscName_…` | M4 (contrôle retiré), M11 |
| Accusé de lecture d'un délégataire : From = boîte, Sender, Return-Path = boîte | `AReadReceiptSentByADelegate_…` | M7 (Sender non posé sur le MDN) |
| Lecture : Sender ≠ From lu (IMAP), égal ou absent → `null` ; persisté en base ; relu hors ligne | `AReceivedMessageWrittenOnBehalfOfItsFrom_…` | M8 (non lu), M9 (égalité au From ignorée), M10 (non persisté) |

Les 11 mutations ont été restaurées par `cp`, et le diff a été vérifié.

**Unitaires** : politique (rôles, `no-reply` : accents, espaces, apostrophes droite et typographique, noms
composés ; domaine ; nom affiché) ; résolveur (rôle × BAL propre : même domaine, autre domaine, ORG, aucune ;
annuaire indisponible ; From ≠ boîte ; nom absent) ; `ExtractSenderAddress` ; `SmtpService` (Sender +
enveloppe, sans Sender, refus sans connexion et tracé) ; `MdnService` délégataire.

**Front** (agent dédié, relu) : mobile et weda2, mention `mail-on-behalf-of`, `replyRecipient()`.
- **Défaut corrigé sur mobile** : un « Répondre » simple ignorait le `Reply-To`.
- Mutations front vues rouges : mobile M1 à M4, weda2 W1 à W3.
- E2E-SHARED-002 v1 est au catalogue (seed `delegataire`, `boite-praticien`, `mail-lu`) et implémenté
  dans les deux suites ; seule la vérification de types a été jouée, l'exécution revient à `/e2e`.

**Passe qualité §Q** :
- api-mail : aucun nettoyage appliqué. La relecture du `Sender` reprend la forme de celle du `From` dans
  chaque projection : c'est voulu, pour la lisibilité.
- mobile : déjà passé au lint par l'agent.
- Aucune re-validation n'était donc nécessaire.

**Correctif issu de `/e2e`** (`client-mobile` `d54017a`) :
- le `From` d'un envoi et l'adresse « à soi » du « Répondre à tous » prennent la boîte ouverte
  (`MailboxSessionService.currentEmail()`), plus le compte ;
- tests unitaires vus rouges sur le code d'avant : compose (`sends From the OPEN mailbox…`), détail
  (`excludes the OPEN mailbox…`) ;
- mobile : 1 381 / 1 381, build et lint verts ;
- weda2 n'était pas concerné : `MSS_USER_EMAIL` y vaut déjà la boîte ouverte.

**À l'humain** :
- weda2 (`feature/nova-mss-weda-integration`) est **non commité**. Le test e2e E2E-SHARED-002, requis
  côté angular, n'existe que dans l'arbre local : à commiter sur TFS avant le merge.
- AIPD à compléter (nom et BAL du délégataire communiqués aux destinataires).

### Correctif après revue humaine (2026-10-30), adresse `no-reply` invalide

- **Constat**, en réponse à la question de l'humain « délégataire sans BAL propre » :
  - la partie locale gardait le point d'une initiale (« J.-P. » → `j.-p.`), ce qui donnait un double
    point ;
  - elle gardait aussi les ligatures et les écritures non latines.
- **Conséquence** : MimeKit levait `ParseException`, l'envoi répondait **500** et rien ne partait.
- **Correctif**, dans `api-mail` `60deec50` :
  - la partie locale ne garde que `[a-z0-9]` et des tirets uniques ;
  - translittération œ→oe, æ→ae, ß→ss, ø→o… ;
  - une partie vide est omise ;
  - repli `no-reply-delegataire@…` quand ni le prénom ni le nom ne sont utilisables.
- **Preuve** :
  - `ADelegateWithAnInitialAndALigature_IsSignedByAValidNoReplyAddress` était rouge avant le
    correctif (500 `Invalid local-part`) ;
  - 12 cas unitaires rouges, dont `NoReplyAddress_IsAlwaysAValidMailboxAddress`.

  Après le correctif : application 3 939 verts, `OnBehalfSendEndToEndTests` 12 verts.

## Sonar log

- Serveur 9.9.8.100196 (`sonar.login`), projet `healthplatform-api-mail`, branche `feat/task-407-…`.
- **Phase 1 (new code)** — 2 analyses :
  - analyse 1 : Quality Gate OK, mais **3 issues** :
    - CA2016 (`MdnService` : le jeton n'était pas transmis à `GetMailboxSenderIdentityAsync`) ;
    - CA1859 (`SmtpService.TransmitAsync` déclaré `Task` au lieu de `Task<string>`, récidive à
      l'identique de task-399) ;
    - S3925 (`OnBehalfSendRefusedException`, triplet de constructeurs présent) : marquée FALSE-POSITIVE
      avec le motif SYSLIB0051.

    CA2016 et CA1859 sont corrigées dans `eeb8f1ea` (refactor pur, application 3 927 verts,
    task-407 et accusés de lecture 22 verts) ;
  - analyse 2 : ✓ Quality Gate OK, **0 issue ouverte**, 0 hotspot, new_coverage 96,4 % (cible 95 %).
- **Phase 2 (legacy)** : 0 itération (0 bug, 0 vulnérabilité, 0 code smell).
- Build Release et 5 suites OpenCover : domain 202, application 3 927, infrastructure 699, api 1 306,
  integration 1 075 verts, 16 ignorés, **3 rouges hors task** : les tests « du jour »
  (`FilterTodayEmails…`, `GetFolderTodayAsync…`, `GetFolderNotSeenTodayAsync…`). L'analyse a tourné
  entre 00 h et 02 h (SINCE en UTC, fenêtre connue). Ils étaient verts dans la suite complète de
  `/develop`, jouée la veille.
- `conventions/csharp.md` : CA1859 → 14, S3925 → 8, CA2016 créée (1),
  `projection-dto-dupliquee` → 3.

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 96,5 % | 96,4 % | −0,1 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 | 0 |
| Coverage (projet) | 97,9 % | 97,8 % | −0,1 pt |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

- `client-angular` (code-only, `feature/nova-mss-weda-integration`), base `origin/next`, lint `tag:scope:mss`.
- **Baseline** : 0 erreur ; avertissements préexistants (max-lines, `@example` vide, constructeur
  d'`ActorInMailbox`), aucun introduit par la task. Aucune itération.
- Build et tests : inchangés depuis la validation de `/develop` (`npm run build` weda2 ✓, mss-lib Vitest
  1 405 / 1 405). Arbre identique, pas de rebuild.

## Lint mobile log

- `client-mobile`, branche `feat/task-407-le-delegataire-ecrit-pour-le-compte-du`.
- **Baseline** : `All files pass linting`, soit 0 erreur et 0 avertissement. Aucune itération, aucun commit.
- Build et tests : inchangés depuis la validation de `/develop` (1 379 / 1 379, `858c7a5`), pas de rebuild.

## E2E log

| Voie | Jouée | Résultat | Dépôts couverts |
|---|---|---|---|
| mobile | jouée | ✅ 54 verts, 0 flaky, parité verte | api-mail `eeb8f1ea`, client-mobile `d54017a` |
| angular | jouée | ✅ 65 verts, 0 flaky, parité verte | api-mail `eeb8f1ea`, weda2 `361a255` + arbre non commité, client-mobile/e2e `d54017a` |

**Historique des passages de ce /e2e (le premier passage a bloqué) :**
1. **mobile, 1er passage, rouge : E2E-SHARED-002, deux constats.**
   - **Défaut réel du client mobile**, que le filet a trouvé. Le `From` d'un envoi était l'adresse du
     **compte** (`authSession.userEmail`) et non celle de la **boîte ouverte**. Le délégataire envoyait
     donc depuis son propre compte, et le serveur refuse désormais ce `From` (400
     `MAIL_FROM_NOT_MAILBOX`). Même défaut sur l'adresse « à soi » du « Répondre à tous ». Corrigé côté
     mobile (`d54017a`), avec deux tests unitaires vus rouges (compose, détail).
   - **Défaut du spec** : il lisait l'`aria-label` sur l'hôte `ion-button`, alors qu'il est porté par
     le bouton natif. Corrigé.
2. **angular, 1er passage, rouge : E2E-SETTINGS-003**, aux deux essais. La signature est connue
   (`corps-de-reponse-libere`) : le spec lisait la version dans le corps d'une réponse interceptée,
   déjà libéré. Il la relit désormais au serveur (`OtherDevice.serverVersion()`). E2E-SHARED-002 était
   vert dès ce passage.
3. **Rejeu** : les deux voies sont vertes, et la porte aussi.

**Signaux pour l'humain** (non bloquants) :
- La divergence E2E-MAILBOX-002 [angular] est **à retirer** : weda2 est revenu à la version du
  catalogue (task-395).
- La quarantaine E2E-COMPOSE-002 [angular] (task-350) est verte sur cette voie.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ✅ | — |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 2 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ · divergence (task-395) | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Divergences temporaires ouvertes** (1) :

- E2E-MAILBOX-002 [angular] — le code weda2 de task-378 (écran de panne à l'entrée et son test) n'est pas encore livré sur la branche weda2 ; divergence décidée par l'humain le 2026-10-25 — résorbée par task-395 — **à retirer** : le client est revenu à la version du catalogue

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

> **Ordre de merge** : dtos-mss #56, puis api-mail #328, puis mobile #118.

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/56 — `awaiting-human-merge`
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/328 — `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/118 — `awaiting-human-merge`
- `client-angular` : code-only. L'humain gère le commit, le push TFS et l'ouverture de la PR, sur
  la branche `feature/nova-mss-weda-integration`. **E2E-SHARED-002, requis côté angular, et le
  correctif d'E2E-SETTINGS-003 sont seulement dans cet arbre local : à commiter avant le merge de
  la PR api-mail.** Fichiers modifiés :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/e2e/mss-e2e/support/e2e-backend.ts`
  - `front/libs/mss/src/core/models/mail.model.ts`
  - `front/libs/mss/src/core/utils/reply-all-recipients.util.spec.ts`
  - `front/libs/mss/src/core/utils/reply-all-recipients.util.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.html`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.on-behalf-of.spec.ts`

## Code Review Summary

**APPROVED**. 0 point bloquant.

| Comportement atteignable par un endpoint | Test d'intégration | Preuve rouge |
|---|---|---|
| Envoi par un délégataire : From = boîte, Sender = nom PSC + `no-reply-…`, Return-Path = boîte, trace OnBehalfOf | `OnBehalfSendEndToEndTests.ADelegateWithoutAPersonalMailboxOnTheDomain_…` | M1, M2 |
| BAL personnelle sur le même domaine ou sur un autre | `…SameDomain_…`, `…OnlyOnAnotherDomain_…` | M1, M2, M6 |
| Réponse depuis un brouillon ; envoi confirmé après mise de côté | `ADelegateReplyFromADraft_…`, `ADelegateSendSetAsideWithoutTheCard_…` | M1, M2 |
| Titulaire et membre sans Sender | `TheHolderAndAMember_SendWithoutASender` | M5 |
| From ≠ boîte → 400, rien reçu, refus tracé | `AFromThatIsNotTheMailbox_…` | M3, M11 |
| Nom PSC absent → 400, rien reçu, refus tracé | `ADelegateWithoutAPscName_…` | M4, M11 |
| Accusé de lecture d'un délégataire | `AReadReceiptSentByADelegate_…` | M7 |
| Lecture : Sender ≠ From exposé ; égal ou absent → null ; persisté ; relu hors ligne | `AReceivedMessageWrittenOnBehalfOfItsFrom_…` | M8, M9, M10 |

- ✅ `OnBehalfSender.cs` concentre les règles du référentiel draft en un seul endroit.
- ✅ Le serveur calcule tout et le client ne fournit rien.
- ✅ Jamais de RPPS dans un en-tête.
- ✅ Le rôle et le nom traversent vers les tâches de fond (`CopyIdentityTo`, task-405).
- ✅ Migration `20261029140000` : deux colonnes nullables, aucune opération fantôme (règle 7c).
- ✅ Mobile : le `From` et l'adresse « à soi » viennent de la boîte ouverte. Défaut trouvé par
  E2E-SHARED-002 et corrigé avec deux tests vus rouges.
- ✅ weda2 : la mention passe par l'interpolation Angular, donc le nom tiré de l'en-tête reçu est
  échappé.
- ⚠️ Le refus d'une **réponse** est tracé `MailSend` et non `MailReply`. Ce n'est pas bloquant :
  l'objet et la requête « REFUSED … » le disent.
- ⚠️ Le `Sender` est relu à la main dans 4 projections `Mail → MailDto` copiées. L'unification est
  à faire dans une task dédiée (`conventions/csharp.md`, `projection-dto-dupliquee`, compteur 3).

## Timings

*(généré par `tools/timing/report.sh --task task-407 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 20 s | — | — | — | — |
| /develop | ok | 3 min 13 s | 8 (39 s) | 6 (6 min 49 s) | — | dtos-mss 1B/0T, api-mail 5B/4T, client-mobile 2B/2T, correctif LocalPart no-reply |
| /sonar | ok | 20 min 54 s | 3 (40 s) | 11 (16 min 29 s) | 4 (1 min 18 s) | api-mail 3B/11T |
| /lint-angular | ok | 13 s | — | — | — | — |
| /lint-mobile | ok | 14 s | — | — | — | — |
| /e2e | ok | 44 min 44 s | — | — | — | e2e ×9 (1 h 11 min) |
| /review | ok | 8 min 26 s | 3 (43 s) | 3 (6 min 18 s) | — | api-mail 1B/1T, client-mobile 1B/1T, client-angular 1B/1T |
| /tech-writer | ok | 1 min 19 s | — | — | — | — |
| **Total cycle** | | **1 h 19 min** | **14 (2 min 02 s)** | **20 (29 min 37 s)** | **4 (1 min 18 s)** | |

Autres commandes mesurées : lint ×2 (7.8 s), nuget-wait ×1 (18 s)
