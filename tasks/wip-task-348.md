# todo-task-348.md — Serveur de messagerie résolu par le seul serveur : table de configuration d'abord, autoconfig XML en repli, plus aucune saisie par l'utilisateur (AUD-42)

**Repos**: api-mail, dtos-mss, client-blazor, client-angular
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
- `dtos-mss` (paresseux) : branche créée par `/develop` au moment où il touche le contrat (CLAUDE.md, « Repo à branche PARESSEUSE »)
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (instantané au `/start` : `feature/nova-rewriting-mss`) — humain gère branche, commit, push, PR TFS
- Dépendances vérifiées au `/start` : task-342 archivée (squash `bf02f565` sur develop) ; aucune trace de l'allowlist AUD-42 sur `develop` (`AllowedUserServerHosts`, `UserMailServerHostPolicy` absents) — le revert de `b052826a` / `a592b5f2` a précédé le squash, la vérification de `368ba75b` est sans objet ; `FromUserConfig` présent (3 occurrences dans `MailServerDiscovery.cs`), c'est l'objet de la task.
