# todo-task-348.md — Serveur de messagerie résolu par le seul serveur : table de configuration d'abord, autoconfig XML en repli, plus aucune saisie par l'utilisateur (AUD-42)

**Repos**: api-mail, dtos-mss, client-blazor, client-angular, client-mobile
**Dependencies**: task-342, **après retrait d'AUD-42** : revert de `b052826a` et `a592b5f2` sur `fix/task-342-durcissement-messagerie`, et vérification de `368ba75b` (passe `/simplify`) sur le code de l'allowlist
**Epic**: E009
**Priorité**: **2** — faille majeure (SSRF, jeton PSC présenté à un serveur arbitraire). Elle n'est corrigée par aucune autre task une fois l'allowlist de task-342 retirée.

> **Origine.** Constat **AUD-42** de l'audit du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`). task-342 le corrigeait par une liste
> d'autorisation d'exploitant (`MailServers:AllowedUserServerHosts`, commit api-mail `b052826a`).
> **Décision humaine du 2026-09-28** : cette approche est abandonnée. On ne se fie plus à un serveur
> saisi par l'utilisateur ; le serveur est **toujours résolu côté api-mail**, depuis le domaine de
> l'email du praticien. Cette task remplace AUD-42 dans task-342.

> **`client-mobile` hors périmètre, justifié** : le mobile n'a aucun écran de configuration serveur
> (aucune occurrence d'`autoconfig`, `imapServer` ou `smtpServer` dans `Client/Mobile/src`). Il
> s'appuie déjà entièrement sur la résolution côté serveur.

## Objective

Aujourd'hui, un praticien peut saisir dans ses Paramètres un serveur IMAP/SMTP personnalisé. api-mail
s'y connecte **en priorité** sur la table des domaines (`MailServerDiscovery.FromUserConfig`) et y
présente le jeton PSC en OAuth2. N'importe quel utilisateur authentifié peut donc faire joindre à
api-mail un hôte interne (`redis`, `postgres`, `10.x`, le service de métadonnées du nuage), ou son
propre serveur pour y récupérer des jetons PSC.

Après cette task, **l'utilisateur ne choisit plus aucun serveur**. api-mail résout le serveur à la
connexion à partir du domaine de l'email du praticien (issu de son identité), dans cet ordre :

```
connexion IMAP / SMTP
  1. domaine présent dans MailServers.Domains (appsettings.json) → utilisé, point final
                                                                    (mémoire : ni Redis, ni HTTP)
  2. sinon : résultat autoconfig en cache Redis (succès ou échec)  → utilisé
  3. sinon : https://autoconfig.{domaine}/mail/config-v1.1.xml     → mis en cache, utilisé
  4. sinon : erreur « serveur introuvable pour ce domaine »
```

**L'autoconfig XML n'est qu'un repli.** Pour tout domaine de la table (MSSanté formation, tests
éditeur, Gmail…), il n'est jamais consulté.

### Règles backend (`api-mail`)

1. **Plus aucune lecture du serveur saisi.** `IMailServerDiscovery.GetImapServerConfig` /
   `GetSmtpServerConfig` perdent leur paramètre `userConfig` ; `FromUserConfig` est supprimé. Les
   trois sites d'appel (`ImapConnectionService.cs:87`, `BackgroundImapService.cs:420`,
   `SmtpConnectionFactory.cs:61`) s'alignent sur `MssAccountOnboardingService.cs:54`, qui résout déjà
   par le seul domaine.
2. **Lecture des réglages retirée du chemin de connexion.** La lecture `userSettingsRepository.GetSettingsAsync()`,
   qui ne servait qu'à récupérer le serveur saisi, est supprimée de ces trois sites si elle n'y sert à
   rien d'autre. C'est à vérifier au cas par cas, et chaque retrait est noté dans le Develop log.
3. **Résolution avec repli autoconfig.** Un service de résolution (orientation : `IMailServerResolver`
   asynchrone, qui compose la table et l'autoconfig) remplace l'appel direct au discovery sur ces
   trois sites. Il consulte la table **d'abord** et ne touche ni Redis ni HTTP si le domaine y figure.
4. **Autoconfig durci.**
   - Le téléchargement du XML est limité aux domaines `*.mssante.fr`. Tout autre domaine absent de
     la table aboutit directement à l'étape 4 (erreur), sans requête HTTP.
   - Un XML dont l'hôte IMAP ou SMTP est une adresse IP littérale, ou dont la résolution DNS désigne
     une adresse privée, de bouclage, de lien local, CGNAT ou de multidiffusion, est **rejeté**. Il
     est traité comme un échec.
5. **Cache négatif.** Un échec d'autoconfig (404, timeout, XML invalide ou rejeté) est mis en cache
   **15 min** par domaine. Les succès restent en cache 24 h. Sans ce cache, un domaine sans XML
   relancerait un téléchargement de 5 s à chaque tentative de connexion.
6. **Log dédié « domaine non configuré ».** Il sert à repérer les domaines à ajouter dans
   `MailServers.Domains`.
   - Il est écrit **une seule fois par domaine et par durée de cache** (au téléchargement du XML,
     jamais à chaque connexion).
   - Message au texte fixe : `Mail domain {MailDomain} is not configured in MailServers:Domains — resolved via {Resolution}`.
   - Propriétés : `EventName = "MailDomainNotConfigured"`, `MailDomain`, `Resolution`
     (`xml-autoconfig` | `none`), `ImapHost`, `SmtpHost` (serveurs trouvés, vides sinon).
   - Niveau **Warning** si le XML a donné un résultat, **Error** si rien n'a été trouvé (un praticien
     est bloqué).
   - **Jamais l'email du praticien**, seulement le domaine.
7. **Réglages : les champs serveur sont ignorés, jamais refusés.** `SettingsController.SaveSettings`
   ne persiste plus `ImapServerConfig` / `SmtpServerConfig` : il les met à `null` avant
   l'enregistrement et répond **200**, pas 400. Raison : `client-angular` est déployé par l'humain via
   TFS, à son rythme. Un ancien front continuera d'envoyer ces champs, et un 400 empêcherait le
   praticien d'enregistrer **tous** ses autres réglages. Les valeurs déjà présentes en base sont
   ignorées à la lecture (règle 1). `GET /settings` ne les renvoie plus.
8. **Endpoint d'affichage.** `GET /api/v1/settings/autoconfig?email=…` est remplacé par
   **`GET /api/v1/settings/mail-server`**, sans paramètre.
   - Il résout pour **l'email du praticien connecté** (identité), jamais pour un email passé en
     paramètre. Ça supprime au passage le risque SSRF résiduel du paramètre libre.
   - Il renvoie le serveur réellement utilisé : hôte et port IMAP, hôte et port SMTP, mode (SSL /
     STARTTLS / OAuth2) et **source** (`configuration` | `autoconfig`). S'il n'y a pas de serveur :
     404 `ProblemDetails` (règle 12).
   - L'ancienne route est supprimée. Elle n'a pas d'autre consommateur que les écrans Paramètres
     Blazor et Angular modifiés ici (à vérifier par grep, noté dans le Develop log).
9. **Doublon SMTP supprimé.** `AutoconfigService.GetSmtpConfigFromDomain` code en dur la config SMTP
   de Gmail et de la formation MSSanté, alors que la table `MailServers.Domains` la porte déjà. On la
   remplace par la lecture de la table.
10. **Banc de charge et tests.** Le seed (`tests/mss.mail.loadtest.seed/Program.cs`) et les tests qui
    désignaient un serveur local par `ImapServerConfig` / `SmtpServerConfig` (SMTP, synchro, sweep
    IMAP, smoke loadtest) passent par un **domaine de test déclaré dans `MailServers.Domains`**.
    Dans le profil loadtest de l'AppHost, il est injecté par variables d'environnement
    (`MailServers__Domains__{domaine-banc}__Imap__Host`, etc.) vers localhost ou `$MSS_LOADTEST_MAIL_HOST`.
    Aucune liste d'autorisation n'est réintroduite.

### Contrat (`dtos-mss`) — étape 1 sur 2

- `UserSettingsDto.ImapServerConfig` / `SmtpServerConfig` (`Dtos/UserSettingsDto.cs:114-117`)
  **restent**, marqués `[Obsolete("Ignoré par api-mail depuis task-348 — le serveur est résolu côté serveur. Suppression en étape 2.")]`.
- Nouveau DTO de réponse de `GET /settings/mail-server` (orientation : `MailServerInfoDto`, qui
  réutilise `MailServerConfigDto` pour IMAP et SMTP, plus `Source`).
- `AutoconfigResultDto` : marqué `[Obsolete]` s'il n'a plus de consommateur, sinon laissé intact.
- Publication NuGet puis bump des consommateurs .NET (`api-mail`, `client-blazor`), comme pour tout
  contrat.
- **Étape 2 (hors périmètre, task de suivi à écrire à la livraison)** : suppression des champs du DTO,
  republication, bump, nettoyage du modèle TypeScript Angular (`user-settings.model.ts:78-79`) et des
  valeurs résiduelles en base. À ne lancer que quand tous les fronts déployés sont à jour.

### Fronts (`client-blazor`, `client-angular`)

- **Retrait** des champs hôte/port IMAP et SMTP, et du bouton « détecter les paramètres »
  (Blazor : `SettingsComponent.razor` ; Angular : `mss-settings.component.ts` et son template). Le
  front n'envoie plus `imapServerConfig` / `smtpServerConfig` à l'enregistrement.
- **Encart en lecture seule** à la place, alimenté par `GET /settings/mail-server` :
  > Serveur de messagerie : `mail-psc.formation.mailiz.mssante.fr` (IMAP 143, SMTP 587)
  > Source : configuration plateforme
  - Libellés de source : `configuration` → « configuration plateforme », `autoconfig` →
    « détection automatique ».
  - 404 → message « Aucun serveur de messagerie n'est configuré pour votre domaine. Contactez le
    support. », sans erreur technique affichée.
- Blazor : libellés via `Localizer`. Angular MSS : libellés FR en dur (pas de ngx-translate dans le
  module MSS).
- Angular : **code-only**, aucune opération git (branche, commit, push et PR TFS restent à l'humain).

### Hors périmètre

- Étape 2 du DTO (voir ci-dessus).
- Ajout de nouveaux domaines dans `MailServers.Domains` : c'est une action d'exploitation, alimentée
  par le log de la règle 6.
- `client-mobile` (justifié en tête).

## Definition of Done

- [ ] Build passes (0 errors) — api-mail, dtos-mss, client-blazor, client-angular
- [ ] Tests pass (0 failures) — hors rouges pré-existants identifiés sur `develop`
- [ ] `grep -rn "FromUserConfig\|AllowedUserServerHosts\|UserMailServerHostPolicy" Api/Mail/src` ne renvoie rien
- [ ] Les sites IMAP, synchro et SMTP ne lisent plus `ImapServerConfig` / `SmtpServerConfig` (`grep` dans `Api/Mail/src` limité au DTO et au contrôleur qui les met à `null`)
- [ ] Unit tests du résolveur : domaine de la table → aucun appel au cache ni à HTTP ; domaine absent + cache succès ; domaine absent + cache échec → pas de HTTP ; XML valide → mis en cache 24 h ; XML en échec → cache 15 min ; domaine hors `*.mssante.fr` → pas de HTTP ; XML pointant vers `127.0.0.1`, `10.0.0.1` ou un nom résolu en adresse privée → rejeté
- [ ] Unit test du log : `MailDomainNotConfigured` émis une fois pour deux connexions successives sur le même domaine absent ; niveau Warning (`xml-autoconfig`) ou Error (`none`) ; aucune propriété ne contient l'email
- [ ] Integration test `PUT /settings` avec `imapServerConfig.host = "redis"` → **200**, puis `GET /settings` ne renvoie aucun serveur, et la connexion IMAP suivante vise le serveur du domaine (aucune tentative vers `redis`)
- [ ] Integration test `GET /settings/mail-server` : domaine configuré → 200 avec `source = configuration` ; domaine inconnu → 404 `application/problem+json`
- [ ] L'ancienne route `GET /settings/autoconfig` n'existe plus (test d'intégration → 404) et n'a plus de consommateur (`grep` sur les fronts)
- [ ] `GetSmtpConfigFromDomain` supprimé ; la config SMTP vient de `MailServers.Domains`
- [ ] Seed loadtest et tests SMTP/synchro/sweep passent par un domaine déclaré dans `MailServers.Domains` ; profil loadtest de l'AppHost mis à jour ; smoke loadtest vert
- [ ] `dtos-mss` : champs marqués `[Obsolete]`, DTO de réponse ajouté, package publié, consommateurs .NET bumpés
- [ ] Blazor : UI component test de l'encart (rendu avec source `configuration`, rendu sur 404) ; champs serveur et bouton « détecter » absents
- [ ] Angular : test du composant Paramètres (encart rendu, 404 géré, payload d'enregistrement sans `imapServerConfig` / `smtpServerConfig`)
- [ ] `data-testid` sur l'encart et son message d'absence (Blazor et Angular)
- [ ] Task de suivi « étape 2 — suppression des champs serveur du DTO » écrite en `todo-*` à la livraison

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost`, puis client Blazor et client Angular connectés
   avec une boîte de test sur `medecin.formation.mssante.fr`.
2. **Blazor → Paramètres** : l'encart affiche `mail-psc.formation.mailiz.mssante.fr` (IMAP 143,
   SMTP 587), source « configuration plateforme ». Aucun champ hôte/port, aucun bouton « détecter ».
   Modifier la signature et enregistrer → succès.
3. **Angular → Paramètres** : même vérification.
4. **Faille fermée** : envoyer à la main
   `PUT /api/v1/settings` avec `"imapServerConfig": { "host": "redis", "port": 6379 }` (Swagger ou
   curl avec le jeton de la session) → 200. Puis `GET /api/v1/settings` → aucun serveur renvoyé.
   Rafraîchir la boîte de réception → les mails arrivent (serveur du domaine). Dans Seq, aucune
   connexion vers `redis`.
5. **Log domaine non configuré** : retirer temporairement le domaine de la boîte de test de
   `appsettings.Development.json`, relancer, rafraîchir la boîte → échec de connexion attendu et,
   dans Seq, **un seul** événement `EventName = 'MailDomainNotConfigured'` avec `MailDomain` renseigné,
   `Resolution = none`, niveau Error, sans email. Rafraîchir encore → pas de nouvel événement.
   L'encart affiche « Aucun serveur de messagerie n'est configuré pour votre domaine ». Remettre le
   domaine.
6. **Ancienne route** : `GET /api/v1/settings/autoconfig?email=x@example.com` → 404.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville, biologie
- **Vague Ségur** : V2
- **Exigences DSR honorées** : non applicable — sécurité d'une fonctionnalité existante
- **INS** : non applicable
- **Authentification PS** : PSC / e-CPS inchangée ; le jeton PSC n'est plus jamais présenté à un serveur choisi par l'utilisateur
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable ; autoconfig MSSanté (format `config-v1.1.xml`) conservé en repli
- **Tracé PGSSI-S** : nouveau log d'exploitation `MailDomainNotConfigured`, domaine seul, sans donnée personnelle ni de santé
- **Consentement patient** : non applicable
- **Référentiels métier** : non applicable
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : réduit — plus aucune connexion sortante vers un hôte arbitraire porteuse du jeton PSC

## Branches
- `api-mail` (pushed) : fix/task-348-serveur-resolu-cote-serveur — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-348-serveur-resolu-cote-serveur (depuis `origin/develop` @ `6d6c8dd1`)
- `client-blazor` (pushed) : fix/task-348-serveur-resolu-cote-serveur — https://github.com/codengine-technologies/HealthPlatform.Client/tree/fix/task-348-serveur-resolu-cote-serveur (depuis `origin/develop` @ `2ced0fb`)
- `client-mobile` (pushed, ajouté le 2026-10-04 sur décision humaine — correctif du blocage `/e2e`) : fix/task-348-serveur-resolu-cote-serveur — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-348-serveur-resolu-cote-serveur (depuis `origin/develop` @ `dd92872`)
- `dtos-mss` (paresseux) : branche créée par `/develop` au moment où il touche le contrat (CLAUDE.md, « Repo à branche PARESSEUSE »)
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (instantané au `/start` : `feature/nova-rewriting-mss`) — humain gère branche, commit, push, PR TFS
- Dépendances vérifiées au `/start` : task-342 archivée (squash `bf02f565` sur develop) ; aucune trace de l'allowlist AUD-42 sur `develop` (`AllowedUserServerHosts`, `UserMailServerHostPolicy` absents) — le revert de `b052826a` / `a592b5f2` a précédé le squash, la vérification de `368ba75b` est sans objet ; `FromUserConfig` présent (3 occurrences dans `MailServerDiscovery.cs`), c'est l'objet de la task.

## Develop log

- Repos touched : `dtos-mss` (branche paresseuse créée par `/develop`), `api-mail`, `client-blazor`, `client-angular` (code-only, branche `feature/nova-rewriting-mss`, aucune opération git)
- DTOs published : `HealthPlatform.Dtos.Mss` 509.0.0 → **511.0.0** (run 37128746649). `UserSettingsDto.ImapServerConfig` / `SmtpServerConfig` marqués `[Obsolete]` (étape 1 sur 2), ajout de `MailServerInfoDto` + `MailServerSources` (`configuration` | `autoconfig`)
- Interop published : no interop change
- `AutoconfigResultDto` n'est **pas** dans `dtos-mss` : c'est un type interne d'api-mail (`IAutoconfigService.cs`), rien à marquer côté contrat. Il reste la charge utile du cache d'autoconfig. Côté Blazor, sa copie locale (`IUserSettingsService.cs`) est supprimée avec son unique consommateur.
- Commits :
  - dtos-mss : feat(dto): serveur resolu cote serveur — champs serveur obsoletes, MailServerInfoDto
  - api-mail : `0a0323ca` fix(mail): serveur de messagerie resolu par le seul serveur — plus aucun serveur saisi (59 fichiers, dont 14 `packages.lock.json` où seule la version DTO change)
  - client-blazor : `de15ef9` feat(settings): serveur de messagerie en lecture seule — plus de champs serveur ni de detection

### Ce qui a changé (api-mail)

1. **Plus aucune lecture du serveur saisi** (règle 1) : `IMailServerDiscovery` perd le paramètre `userConfig` et `FromUserConfig`. Méthodes renommées `GetConfiguredImapServer` / `GetConfiguredSmtpServer` (elles ne lisent que la table), plus `IsConfiguredDomain`.
2. **Lecture des réglages retirée du chemin de connexion** (règle 2), vérifiée site par site. Dans `ImapConnectionService`, `BackgroundImapService` et `SmtpConnectionFactory`, `IUserSettingsRepository.GetSettingsAsync()` ne servait **qu'à** récupérer le serveur saisi : la dépendance est retirée des trois constructeurs. `SmtpService` garde sa lecture des réglages, qui sert l'identité d'expéditeur.
3. **`IMailServerResolver`** (règle 3) : la table d'abord (un domaine présent, même incomplet, ne touche ni Redis ni HTTP), puis l'autoconfig, puis `null`. Les trois sites l'utilisent. Il est enregistré dans `AddApplication`, à côté de la découverte, et non plus côté API : les compositions de test qui passent par `AddApplication` le reçoivent.
4. **Autoconfig durci** (règles 4, 5, 6, 9) :
   - `*.mssante.fr` seulement, aucune requête HTTP sinon ;
   - IP littérale, ou résolution DNS non publique (privée, bouclage, lien local, CGNAT, multidiffusion, réservée, IPv6 ULA ou lien local, IPv4 transportée en IPv6) → rejet ;
   - échec en cache 15 min, succès 24 h, sous une clé nouvelle (`mail-autoconfig:`) pour ne pas relire l'ancien type ;
   - log `MailDomainNotConfigured` au téléchargement seulement (une fois par domaine et par durée de cache), texte fixe, `EventName` / `ImapHost` / `SmtpHost` en portée, Warning (`xml-autoconfig`) ou Error (`none`), jamais l'email ;
   - `GetSmtpConfigFromDomain` supprimé ;
   - un serveur découvert est toujours joint avec validation TLS.
5. **Réglages** (règle 7) : `SaveSettings` met les deux champs à `null` et répond 200. `GET /settings` ne les renvoie plus : les valeurs résiduelles en base sont ignorées.
6. **Endpoint** (règle 8) : `GET /api/v1/settings/mail-server`, pour l'identité connectée, 404 `ProblemDetails` sans serveur. `GET /settings/autoconfig?email=` est supprimé. Grep : aucun autre consommateur que les écrans Paramètres Blazor et Angular modifiés ici, et `client-mobile` n'y faisait aucune référence.
7. **Bancs** (règle 10) : l'AppHost déclare le domaine du banc de charge et celui du filet e2e.
   - Banc de charge : `MailServers__Domains__{MSS_LOADTEST_DOMAIN ?? loadtest.local}__…` vers Toxiproxy 13993/13465 ; en direct 3993/3465 avec `MSS_LOADTEST_NO_PROXY=true` ; vers les NodePorts 30993/30465 avec `MSS_LOADTEST_MAIL_HOST`.
   - Filet e2e : `e2e.test` vers Dovecot 3993 et GreenMail 3465. **Découvert en cours de route** : le seed e2e choisissait lui aussi son serveur par les réglages. Sans cette déclaration, tout `/e2e` serait tombé.
   - Les deux seeds n'envoient plus de serveur, et vérifient celui que résout api-mail (`GET /settings/mail-server`).
   - Garde ajoutée : `E2eProfile.MailDomain == E2eSeedPlan.Domain`.
   - Aucune liste d'autorisation n'est réintroduite.
8. **Asymétrie assumée** : `MssAccountOnboardingService` (test de connexion d'une nouvelle boîte, E016) reste sur la **table seule**. Son email vient d'une saisie libre : lui donner l'autoconfig rouvrirait un téléchargement déclenchable de l'extérieur. Un domaine résolu seulement par autoconfig fonctionne donc à la connexion, mais pas encore à l'onboarding. À arbitrer si le cas se présente.

### Fronts

- **client-blazor** :
  - champs hôte/port et boutons « Détecter » / « Enregistrer la configuration » retirés ;
  - encart `MailServerInfoCard` (`data-testid` `settings-mail-server`, `-summary`, `-source`, `-missing`) ;
  - libellés via `Localizer` (FR et EN), anciennes clés retirées ;
  - `GetMailServerAsync()` en lecture silencieuse : un 404 n'affiche pas d'erreur technique.
- **client-angular** (code-only) :
  - signaux et méthodes serveur retirés ;
  - encart en lecture seule (mêmes `data-testid`), libellés FR en dur ;
  - `MssApiService.getMailServer()` remplace `autoDetectServerConfig(email)` ;
  - `withoutServerSelection()` retire les deux champs de **chaque** enregistrement ;
  - champs du modèle TS marqués `@deprecated` (suppression en étape 2) ;
  - règles SCSS mortes retirées.

### Tests d'intégration (règle 1b) — comportement → test → preuve rouge

`SettingsMailServerEndpointIntegrationTests` monte la vraie route, le vrai `SettingsController`, le vrai `UserSettingsRepository` (PostgreSQL du fixture, base isolée), les vrais `MailServerResolver` / `MailServerDiscovery` / `AutoconfigService` et le vrai `ImapConnectionService`. Seuls sont simulés le serveur HTTP d'autoconfig (il compte ses appels) et le client IMAP (il note l'hôte visé, puis refuse la connexion).

| Comportement lu dans la réponse réelle | Test | Rouge par mutation |
|---|---|---|
| `POST /settings` avec `imapServerConfig.host = "redis"` → 200 ; `GET /settings` → aucun serveur ; la connexion IMAP suivante vise le serveur du domaine, jamais `redis` | `PostingAServer_IsAccepted_ButNeverStoredNorReturned_AndTheNextImapConnectionTargetsTheDomainServer` | A (vidage retiré) : `Assert.Null() … Actual: MailServerConfigDto { Host = "redis", Port = 6379 … }` ; B (table ignorée) : `Expected to receive exactly 1 call matching ConnectAsync(imap.cabinet-348.test.local, 143, StartTls…)` |
| `GET /settings/mail-server`, domaine configuré → 200, `source = configuration`, sans HTTP | `GetMailServer_ConfiguredDomain_Returns200_WithSourceConfiguration` | B : `Expected: OK Actual: NotFound` |
| `GET /settings/mail-server`, domaine inconnu → 404 `application/problem+json`, sans HTTP | `GetMailServer_UnknownDomain_Returns404ProblemDetails_WithoutAnyHttpOutsideMssante` | route absente avant la task |
| `GET /settings/autoconfig?email=…` → 404, aucun téléchargement | `OldAutoconfigRoute_NoLongerExists` | route présente avant la task |

Mutations unitaires sur l'autoconfig :
- C (tout domaine téléchargé) → 5 rouges `DomainOutsideMssante…` ;
- D (plages non publiques ignorées) → 7 rouges `XmlHostResolvingToANonPublicAddress…` ;
- E (échec non mis en cache) → 13 rouges (`Failure_IsCached15Minutes`, `TwiceForAFailingDomain_DownloadsOnlyOnce`, log Error unique…).

**Vert qui ment, trouvé et corrigé.** Le test « IP littérale » restait vert sans le garde des littéraux : le DNS scripté ne résolvait pas le littéral, et tous les cas étaient non publics. Ajout de deux littéraux publics et d'un DNS qui les résout comme le vrai : rouges sous mutation. Prévention : `conventions/csharp.md` § `test-de-rejet-attribuable`.

### Tests unitaires et de composants (DOD)

- **Résolveur** (`MailServerResolverTests`) : table → aucun appel au cache ni à HTTP ; absent + cache succès ; absent + cache échec → pas de HTTP ; hors `*.mssante.fr` → pas de HTTP ; port invalide écarté ; email vide ou sans domaine.
- **Autoconfig** (`AutoconfigServiceTests`) :
  - XML valide → cache 24 h ; échecs (404, XML invalide, sans serveur) → cache 15 min ;
  - `127.0.0.1`, `10.0.0.1`, `169.254.169.254`, `[::1]` et des littéraux publics → rejet ;
  - nom résolu en `10.x`, `192.168.x`, `172.20.x`, `127.x`, `100.64.x`, `169.254.x`, `fd00::1` → rejet ;
  - log `MailDomainNotConfigured` unique sur deux appels, Warning ou Error, aucune propriété ne contient `@`.
- `NonPublicNetworkAddressTests` (plages, bornes CGNAT et 172.16/12, IPv4 transportée en IPv6) ; `SettingsControllerTests` (vidage à l'aller et au retour, `mail-server` 200 / 404 / sans email, ancienne route absente).
- **Blazor** (bUnit) `MailServerInfoCardTests` : encart `configuration`, libellé `autoconfig`, message sur 404, écran sans champ serveur ni bouton « détecter ».
- **Angular** (vitest) `mss-settings.component.spec.ts` : encart, libellé autoconfig, 404 géré sans erreur technique, aucun `#imap-host` / `#auto-detect-server`…, payload d'enregistrement sans `imapServerConfig` / `smtpServerConfig` (même si les réglages lus en portaient), `withoutServerSelection`.
- **Tests réécrits parce qu'ils éprouvaient le défaut** :
  - 6 tests de `MailServerDiscoveryTests` (« UserConfigOverridesDefault »…) supprimés ; `GetAutoconfigForDomain` → `IsConfiguredDomain` ;
  - `AutoconfigServiceCoverageTests` et `AutoconfigServiceCacheTests` (ancienne API, domaine quelconque téléchargé) supprimés, couverts par le nouveau `AutoconfigServiceTests` ;
  - `SmtpConnectionFactoryTests` : « WithCustomSmtpConfig_UsesCustomConfig » et « WithNullUserSettings_UsesAutodiscovery » supprimés ;
  - `ImapConnectionServiceTests.UserSettingsRepositoryShouldReturnDefaultSettings` (il ne testait que la doublure) supprimé.

### Vérification locale

- **dtos-mss** : build 0 erreur, 0 avertissement.
- **api-mail** : build 0 erreur ; domain 190/190, infrastructure 675/675, api 1 161/1 161, application 3 415/3 415 ; intégration **748 réussis, 9 rouges, 16 ignorés**. Les 9 repassent seuls (12/12 avec leurs voisins de classe) :
  - 3 × `different vector dimensions 3 and 1536` (base partagée) ;
  - `Le_maintien_des_partitions…` et `…ShareOneProvisioning` ;
  - 4 × `53300: sorry, too many clients already` (Postgres local partagé avec l'AppHost en cours).

  Exécuté avec `--artifacts-path artifacts` dans le dépôt, l'AppHost tournant.
- **client-blazor** : build 0 erreur ; 396 réussis, 0 échec, 2 ignorés.
- **client-angular** : spec des Paramètres 6/6 (vitest). Le build et la suite complète reviennent à `/lint-angular` (pipeline aligné, avec rollback).
- **Smoke loadtest** (`SmtpSessionReuseBenchSmokeTests`) vert, sur un domaine déclaré dans la table.

### Passe qualité (§Q)

- Faite en relecture ciblée du diff, sans lancer la skill `/simplify` :
  - S1067 évité dès l'écriture (plages réseau en table plutôt qu'une chaîne de `||`) ;
  - S1075 : URL d'autoconfig construite par `UriBuilder` ;
  - paramètre homonyme renommé dans l'AppHost ;
  - BOM des fichiers rétablis à l'identique de `develop` ;
  - règles SCSS mortes retirées côté Angular.

  Aucun cleanup supplémentaire appliqué, donc pas de re-validation.
- Skipped (contract) : dtos-mss.

### DOD self-check

- [x] Build 0 erreur sur dtos-mss, api-mail et client-blazor ; client-angular compilé par vitest (build complet : `/lint-angular`)
- [x] Tests 0 échec, hors rouges pré-existants ou environnementaux identifiés (rejoués seuls, verts)
- [x] `grep FromUserConfig|AllowedUserServerHosts|UserMailServerHostPolicy Api/Mail/src` → vide
- [x] `ImapServerConfig` / `SmtpServerConfig` dans `Api/Mail/src` : seulement `SettingsController.DropServerSelection`, qui les met à `null`
- [x] Unit tests du résolveur, de l'autoconfig et du log (listes ci-dessus)
- [x] Integration test `POST /settings` avec `host = "redis"` → 200, `GET` sans serveur, connexion IMAP vers le serveur du domaine. La route réelle est `POST /api/v1/settings` ; la DOD écrivait `PUT`.
- [x] Integration test `GET /settings/mail-server` : 200 `configuration` / 404 `problem+json`
- [x] Ancienne route → 404 (test d'intégration), et plus aucun consommateur (grep fronts)
- [x] `GetSmtpConfigFromDomain` supprimé ; le SMTP est lu dans `MailServers.Domains`
- [x] Seed loadtest et tests SMTP / synchro / sweep sur un domaine déclaré ; profil loadtest de l'AppHost mis à jour ; smoke vert
- [x] dtos-mss : `[Obsolete]`, DTO de réponse ajouté, package publié, consommateurs .NET bumpés
- [x] Blazor : tests de composant de l'encart (configuration, 404) ; champs serveur et bouton absents
- [x] Angular : test du composant (encart, 404, payload sans serveur)
- [x] `data-testid` sur l'encart et sur son message d'absence (Blazor et Angular)
- [x] Task de suivi écrite : `tasks/todo-task-351.md` (étape 2, avec un encadré d'arbitrage humain sur la condition de lancement)
- Next step : /sonar task-348

### Reprise après `/e2e` rouge (2026-10-04)

- **Fusion d'`origin/develop`** (task-331 mergée) dans les branches task-348, par merge (règle 4) :
  - dtos-mss `41b0f14`, republié en **HealthPlatform.Dtos.Mss 514.0.0** (run 514), qui porte les contrats de task-348 et de task-331. `develop` référençait 510.0.0 et la branche 511.0.0 : aucun des deux ne les portait tous ;
  - api-mail `5f1218ba` et client-blazor `e851c5b`, alignés sur 514.0.0.
  - Vérification : unitaires api-mail verts (domain 190, infrastructure 690, application 3 432, api 1 175), Blazor 413. Intégration : 8 rouges, dont 5 passent seuls ; les 3 tests « du jour » échouent à 00:14 heure locale, la fenêtre 00:00–02:00 déjà connue sur `develop`.
- **Diagnostic du rouge mobile `E2E-DETAIL-002`** (vert sur task-348 seule et sur task-331 seule, rouge 3/3 ensemble) :
  - l'API rend le corps (`content/1` : 200, 46 à 78 ms, corps texte et HTML présents) ;
  - la chronologie de la trace montre l'attente « corps visible » satisfaite à 3,25 s, alors que la requête `content/1` n'est partie qu'à 3,28 s ;
  - pendant le chargement, `mail-body` rendait un `<pre data-testid="mail-body-plain">` vide **et** « Aucun contenu disponible pour ce courrier ». Le test lisait donc un placeholder, et l'écran montrait un instant un courrier vide.
  - Le code fautif est antérieur aux deux tasks. La combinaison n'a fait que décaler l'arrivée du contenu ; la cause de ce décalage n'est pas isolée.
- **Correctif** (`client-mobile` ajouté aux Repos sur décision humaine, `aa80cad`) :
  - `mail-body` affiche un squelette (`mail-body-loading`) tant que le contenu n'est pas arrivé ; l'état vide n'apparaît que pour un contenu chargé et vide ;
  - `E2E-DETAIL-002` attend en headless un corps non vide (`toContainText(/\S/)`).
  - Tests de composant : squelette pendant le chargement, **vu rouge** (`squelette: Expected null not to be null`) ; état vide seulement sur un contenu vide ; corps sans squelette une fois chargé.
  - Mobile : build OK, **994/994**, lint propre (« All files pass linting »).

## Sonar log

- Serveur : SonarQube 25.6.0.109173 (`sonar.token`), port 9001, démarré au pré-flight (base puis serveur). Projet `healthplatform-api-mail`, période de nouveau code « previous version » depuis le 2026-04-17 : elle englobe des dizaines de tasks déjà mergées, d'où un tri par provenance de chaque finding.
- **Phase 1 (nouveau code de task-348) : verte** en 2 itérations.
  - Itération 1, sur les fichiers de la task : **2 issues** (S4457 `MailServerResolver.ResolveAsync`, S138 `AddApplication`) et **11 hotspots** S1313 (`NonPublicNetworkAddress`). Couverture du nouveau code sous 95 % sur `SettingsController` (92,7), `AutoconfigService` (94,0), `MailServerResolver` (94,9), `DnsHostAddressResolver` (50).
  - Corrigé : S4457 (validation hors du corps async, `ResolveCoreAsync` privée) ; S1313 (plages en octets, `IPAddress.IPv6Any` / `IPv6Loopback`) ; S138 : **dette antérieure** (issue créée le 2026-09-07), réduite et non introduite (`AddApplication` : 196 lignes sur `develop`, 192 après extraction de `AddMailServerResolution`).
  - +8 tests de couverture (annulation par l'appelant, pannes de transport et inattendue, annulation pendant la résolution DNS, serveur partiel, validation à l'appel, DNS système, `GetMailServer` IMAP seul, réglages absents). Au passage, `AutoconfigService` contrôle désormais un jeton déjà annulé dès l'entrée (il téléchargeait et mettait en cache quand le fournisseur ignorait le jeton).
  - Itération 2 : **aucune issue ni aucun hotspot** sur les fichiers de la task ; couverture du nouveau code de ces fichiers 95,8 à 100 %.
- Contrôle mécanique §Q 2b (sauté en `/develop`, lancé ici) : 2 commentaires au motif S125 réécrits (`f4824ab7`). S4457 n'aurait **pas** été attrapé : le grep ne cherche que `ThrowIf…`, alors que le code levait un `throw new ArgumentException` explicite.
- Findings restants du nouveau code, tous **hors task-348** (provenance vérifiée) : 66 violations et 13 hotspots `TO_REVIEW` hérités, dont 2 apparus à cette analyse mais venus de task-329 (#270, mergée après la précédente analyse) : S103 `DraftService.cs:330`, S138 `SmtpService.SendMailAsync`.
- Phase 2 (dette héritée) : **non lancée** (optionnelle, hors périmètre de la task).
- Build / tests : Release, 0 erreur ; unitaires verts. Les rouges d'intégration des passes de couverture sont tous `53300: sorry, too many clients already` (Postgres local partagé avec l'AppHost en cours) ; les mêmes tests passent seuls.
- Commits : `9dd688e3` fix(sonar/new) S4457 / S1313 / S138 ; `b47c0158` test(sonar/new) ; `f4824ab7` refactor(sonar/new) S125.
- Conventions : S4457 → 5 (récidive), S125 → 10, **S1313 ajoutée**.

### KPIs qualité (baseline → final)

| Métrique | Baseline (analyse du 2026-10-01) | Final (branche task-348) | Δ |
|---|---|---|---|
| Quality Gate (nouveau code) | ERROR | ERROR | → (conditions héritées : hotspots non revus, violations) |
| New coverage | 98,2 % | 98,1 % | −0,1 pt |
| Bugs | 2 | 2 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 15 | 15 | 0 (24 → 13 sur le nouveau code après correction des 11 de la task) |
| Code smells | 65 | 68 | +3, tous venus de task-329 (#270) mergée entre-temps, aucun de task-348 |
| Reliability / Security / Maintainability | D / A / A | D / A / A | → |
| Coverage (global) | 98,0 % | 98,0 % | 0 |

## Lint log

- `/lint-angular` (Mode A, code-only, aucune opération git hors `git fetch origin next`) : base `origin/next`, scope `tag:scope:mss`.
- Baseline : **3 erreurs**, toutes `prettier/prettier` dans les fichiers de la task (`mss-api.service.ts` ×2, `mss-settings.component.ts` ×1 : retours à la ligne et fins de ligne CRLF), et 34 avertissements `jsdoc/require-example`, dette existante du module.
- Itération 1 : auto-fix (`-- --fix`) → **0 erreur**. Fixes de l'auto-fixer seulement, donc rien à consigner dans `conventions/angular.md`.
- Constat d'outillage : le filtre `--projects=tag:scope:mss` ne restreint pas `nx affected` (les 12 projets affectés ont été lintés et auto-fixés). Vérifié par date de modification : seuls `libs/mss/src/core/services/mss-api.service.ts` et `libs/mss/src/features/settings/mss-settings.component.ts` ont changé.
- Build (pipeline aligné, périmètre affecté complet) : **10/11 projets verts**, dont `weda2`, qui consomme `mss-lib`. `mss:build:production` échoue sur un fichier d'environnement absent du poste (`apps/mss/src/environments/environment.prod.ts` : seul `environment.ts` existe). Fichier non touché par la task, échec d'environnement local et non régression.
- Tests (pipeline aligné) : **11/11 projets verts**.
- Itérations consommées : 1 / 5.

## Lint mobile log

- 1ᵉʳ passage : **skipped**, `client-mobile` n'était pas listé dans `**Repos**:`.
- 2ᵉ passage (2026-10-04, `client-mobile` ajouté pour le correctif de `mail-body`) : `npm run lint` → **All files pass linting**, 0 itération de correction nécessaire. Build et tests verts (994/994).

## E2E log

> 3ᵉ passage (2026-10-04), **vert**. Branches task-348 fusionnées avec `origin/develop` (task-331, DTO 514.0.0) ; `client-mobile` ajouté pour le correctif de `mail-body`. Les deux passages rouges précédents sont résolus : `E2E-PATIENT-002` est arrivé au catalogue avec la fusion de task-331 ; `E2E-DETAIL-002` (mobile) est corrigé par le squelette de chargement et l'attente d'un corps non vide ; `E2E-SEARCH-001` (Angular) est corrigé par un prédicat qui fixe `POST /api/v1/search/semantic` (le test capturait `GET /search/history`, sans corps). Fichier Angular modifié en code-only, sans opération git : `front/e2e/mss-e2e/specs/functional.e2e.ts`.

| Voie | Jouée | Résultat | Détail |
|---|---|---|---|
| mobile | oui (`api-mail`, `client-mobile`, `dtos-mss`) | ✅ vert | 27 réussis, 0 flaky, 0 rouge — branche `fix/task-348-…` (`aa80cad`) |
| angular | oui (`api-mail`, `client-angular`, `dtos-mss`) | ✅ vert | 27 réussis, 0 flaky, 0 rouge — branche humaine `feature/nova-rewriting-mss` |
| porte | — | ✅ vert (code 0) | parité verte |

Démontage vérifié : ports 5052 / 8100 / 4200 / 3993 / 3465 / 3143 libres, aucun conteneur `e2e-*` résiduel.

Écrans touchés sans scénario e2e modifié (avertissement non bloquant) : l'écran Paramètres Angular (`mss-settings.component.html`) — aucun parcours médecin créé, encart couvert par le test de composant. `mail-body` (mobile) est couvert par `E2E-DETAIL-002`, durci.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 1 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Timings

*(généré par `tools/timing/report.sh --task task-348 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 57 s | — | — | — | — |
| /develop | ok | 52 min 07 s | 7 (2 min 07 s) | 8 (8 min 55 s) | — | dtos-mss 1B/0T, api-mail 2B/4T, client-blazor 3B/3T, client-mobile 1B/1T |
| /sonar | ok | 30 min 11 s | 2 (1 min 23 s) | 10 (9 min 59 s) | 4 (5 min 07 s) | 2 itération(s), api-mail 2B/10T |
| /lint-angular | ok | 11 min 54 s | 1 (1 min 35 s) | 1 (4 min 51 s) | — | 1 itération(s), client-angular 1B/1T |
| /lint-mobile | skipped | 2.2 s | — | — | — | client-mobile non listé dans Repos |
| /e2e | ok | 18 min 00 s | — | — | — | e2e ×11 (37 min 31 s) |
| /review | ok | 11 min 39 s | 4 (1 min 17 s) | 3 (4 min 25 s) | — | dtos-mss 1B/0T, api-mail 1B/1T, client-blazor 1B/1T, client-mobile 1B/1T |
| /tech-writer | ok | 1 min 29 s | — | — | — | — |
| **Total cycle** | | **2 h 06 min** | **14 (6 min 23 s)** | **22 (28 min 11 s)** | **4 (5 min 07 s)** | |

Autres commandes mesurées : lint ×3 (3 min 41 s), nuget-wait ×2 (20 s), restore ×1 (3.0 s)

## PRs

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/41 — label `awaiting-human-merge`
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/273 — label `awaiting-human-merge`
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/89 — label `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/86 — label `awaiting-human-merge`
- `client-angular` : code-only — l'humain gère le commit, le push TFS et l'ouverture de la PR. Branche `feature/nova-rewriting-mss`, build et tests verts. Fichiers modifiés par la forge :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/libs/mss/src/core/models/user-settings.model.ts`
  - `front/libs/mss/src/core/services/mss-api.service.ts`
  - `front/libs/mss/src/features/settings/mss-settings.component.html`
  - `front/libs/mss/src/features/settings/mss-settings.component.scss`
  - `front/libs/mss/src/features/settings/mss-settings.component.ts`
  - `front/libs/mss/src/features/settings/mss-settings.component.spec.ts`
  - ⚠️ Également modifiés dans l'arbre de travail, **pas par la forge** (à ne pas inclure sans vérification) :
    - `front/apps/mss/src/environments/environment.ts`
    - `front/apps/weda2/src/environments/environment.ts`

## Code Review Summary

**Verdict : APPROVED** — 0 bloquant, 4 suggestions (non bloquantes).

- ✅ `SettingsController` : serveur saisi ignoré (mis à `null`, 200) à l'aller comme au retour ; `GET /settings/mail-server` résolu pour l'identité connectée, 404 `ProblemDetails` (règle 12) ; ancienne route `autoconfig?email=` supprimée.
- ✅ `MailServerResolver` / `MailServerDiscovery` : la table d'abord (ni Redis ni HTTP pour un domaine configuré), autoconfig en repli ; plus aucune lecture d'un serveur saisi sur les trois sites de connexion (`IUserSettingsRepository` retiré de leurs constructeurs).
- ✅ `AutoconfigService` : limité à `*.mssante.fr`, IP littérale et adresses non publiques rejetées, échec en cache 15 min, log `MailDomainNotConfigured` sans email.
- ✅ Bancs : domaines du banc de charge et du filet e2e déclarés dans `MailServers:Domains` par l'AppHost (jamais `appsettings.json`) ; seeds sans serveur.
- ✅ `client-mobile` (`mail-body`) : squelette pendant le chargement, état vide seulement sur un contenu chargé et vide ; `E2E-DETAIL-002` attend un corps non vide.
- ⚠️ Suggestion — DNS rebinding : l'hôte d'un autoconfig est contrôlé au téléchargement, puis re-résolu à la connexion. Risque résiduel faible (domaines `*.mssante.fr` seulement, DNS de l'espace de confiance) ; à traiter si l'autoconfig s'ouvre à d'autres domaines.
- ⚠️ Suggestion — deux connexions simultanées sur un domaine absent du cache peuvent télécharger deux fois et écrire deux logs `MailDomainNotConfigured` (course sans conséquence fonctionnelle).
- ⚠️ Suggestion — `MssAccountOnboardingService` reste sur la table seule (email de saisie libre) : un domaine résolu seulement par autoconfig fonctionne à la connexion, pas encore à l'onboarding.
- ⚠️ Suggestion — mobile : si le chargement du contenu échoue, le squelette reste affiché sous le bandeau d'erreur explicite ; afficher l'état d'erreur dans `mail-body` serait plus cohérent.

**Règle 1b (tests d'intégration d'endpoint, vus rouges)** :

| Comportement | Test | Preuve rouge |
|---|---|---|
| `POST /settings` avec un serveur « redis » → 200, non stocké, non renvoyé, et la connexion IMAP suivante vise le serveur du domaine | `SettingsMailServerEndpointIntegrationTests.PostingAServer_IsAccepted_ButNeverStoredNorReturned_AndTheNextImapConnectionTargetsTheDomainServer` | mutation A (vidage retiré) et B (table ignorée) |
| `GET /settings/mail-server`, domaine configuré → 200, `source = configuration`, sans HTTP | `GetMailServer_ConfiguredDomain_Returns200_WithSourceConfiguration` | mutation B |
| `GET /settings/mail-server`, domaine inconnu → 404 `problem+json` | `GetMailServer_UnknownDomain_Returns404ProblemDetails_WithoutAnyHttpOutsideMssante` | route absente avant la task |
| Ancienne route `autoconfig?email=` → 404 | `OldAutoconfigRoute_NoLongerExists` | route présente avant la task |

## Merged

- 2026-10-04, squash-merge par `/merge task-348 --i-tested` (HAG : plan de test manuel validé par l'humain).
- `dtos-mss` #41 → `c17aaff2` (CI develop verte : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/actions/runs/37192662891)
- `api-mail` #273 → `9452245c` (CI develop verte : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/37192675041)
- `client-blazor` #89 → `e0175434` (CI develop verte : https://github.com/codengine-technologies/HealthPlatform.Client/actions/runs/37192689213)
- `client-mobile` #86 → `bee14d01` (CI develop verte)
- `client-angular` : géré par l'humain (TFS).
- Branches `fix/task-348-serveur-resolu-cote-serveur` supprimées (distantes et locales) ; aucune branche staging concernée.
