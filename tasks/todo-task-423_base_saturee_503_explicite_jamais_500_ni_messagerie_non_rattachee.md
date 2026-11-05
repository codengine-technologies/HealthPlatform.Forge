# todo-task-423.md — Base saturée : le médecin reçoit « service momentanément indisponible », jamais une erreur inattendue ni « messagerie non rattachée »

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E015
**Single frontend**: true
**Priorité**: **1**. Quand la base sature, une partie des médecins reçoit un message **faux** : « Cette
messagerie n'est pas rattachée à votre compte ». Ils croient leur boîte détachée et peuvent tenter de la
rattacher à nouveau, alors que le service est seulement indisponible quelques instants. Une autre partie
reçoit une erreur inattendue (500) au lieu d'un 503. Les deux violent la règle 12.

> **Origine.** Campagne « limites » du 2026-11-05, itération 1 (escalier `journey`, IA simulée). Rapport :
> `Api/Mail/tests/loadtest-k6/reports/2026-11-05/report-journey-escalier-1996-20261104-ia-simulee-013324.md`,
> findings **F2** et **F3**. Au palier 1400, Postgres atteint `max_connections` (task-422). La plupart des routes
> répondent alors correctement **503 `DATABASE_UNAVAILABLE`** (12 017 réponses), mais pas toutes.

## Ce qui est établi

| Réponse rendue | Nombre | Route ou chemin | Ce qu'elle devrait être |
|---|---|---|---|
| 503 `DATABASE_UNAVAILABLE` | 12 017 | `GlobalExceptionHandler`, la plupart des routes | correct (règle 12) |
| **500** « An unexpected error occurred » | **4 323** | `GET /api/v1/mail/folders` | 503 `DATABASE_UNAVAILABLE` |
| **403 `MAILBOX_NOT_ATTACHED`** / `MAILBOX_REQUIRED` | **915** | toute route qui exige une boîte | 503 `DATABASE_UNAVAILABLE` |

- **F2 — le 500, cause établie** (Seq, trace `b1536922e2b4a591660bab9ec1742e48`, 2026-11-04T23:58:51Z) :
  `ImapService.GetFoldersAsync` (`Api/Mail/src/Application/Services/Implementation/ImapService.cs`, autour de
  la ligne 310) entoure `PersistAndReconcileFoldersAsync` d'un `catch (Exception)` qui journalise « Unexpected
  error getting folders » et rend `Result.Error`, donc un 500 générique. L'exception Npgsql
  (`08P01 server_login_retry`) n'atteint jamais le `GlobalExceptionHandler`, qui l'aurait classée
  `DATABASE_UNAVAILABLE`. Le même message existe dans `ImapFolderService.cs` (ligne 154) et une seconde fois
  dans `ImapService.cs` (ligne 293) : les trois sont à examiner.
- **F3 — le 403, chaîne probable, à établir trace par trace.**
  - Au même instant, `TenantRegistrySynchronizer.SynchroniseAsync` reçoit une `TenantRegistryUnavailableException`
    (`53300` en connexion directe au registre). Il journalise « Synchronisation ignorée — registre indisponible »
    et continue, par conception : « la cartographie du parc ne doit jamais coûter au praticien l'accès à sa
    messagerie ».
  - La sélection de la boîte (`UserContextEnricherMiddleware`) aboutit ensuite à `NotAttached` ou
    `MailboxRequired`, rendus en 403.
  - Une panne d'infrastructure est donc présentée comme une **réponse métier** sur les droits du médecin.
    Le contrat de `ITenantRegistryClient.GetMailboxAsync` dit pourtant : « `null` … c'est une réponse
    (403 `MAILBOX_NOT_ATTACHED`), **pas une panne** ».

## Objective

Quand la base ou le registre est indisponible, **toute** route rend un **503 `DATABASE_UNAVAILABLE`** en
`application/problem+json` (règle 12), produit par le `GlobalExceptionHandler`. Jamais un 500 générique, jamais
un 403 sur le rattachement. Le médecin lit « service momentanément indisponible, réessayez », et ses clients
gardent le comportement déjà prévu pour un 503.

Règles métier :
- **Un 403 de rattachement n'est rendu que sur une réponse du registre**, jamais sur son absence de réponse. Si
  le registre n'a pas pu être lu, on ne sait pas si la boîte est rattachée : c'est une indisponibilité.
- **La synchronisation du parc reste au mieux** : quand seule la cartographie (dernière activité, dernière
  authentification) échoue et que la sélection de la boîte peut être tranchée, la requête du médecin passe. Ce qui
  change, c'est qu'une sélection **impossible à trancher** faute de registre devient un 503, plus un 403.
- **Aucune heuristique de message** : le classement se fait par type d'exception ou par SQLSTATE, comme le fait
  déjà le `GlobalExceptionHandler`.
- **Zéro fuite** : le `detail` ne porte ni message d'exception brut, ni nom de base, ni adresse de boîte.

### Hors périmètre

- Éloigner le mur lui-même : task-422.
- Les clients (`client-mobile`, `client-blazor`, `client-angular`) : ils lisent déjà `ProblemDetails` et
  traitent le 503. Aucun écran ne change. Si `/develop` constate qu'un client traite un 503 de façon incorrecte
  sur ces routes, il ouvre une question au lieu d'élargir les `**Repos**`.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`. Exception admise : les 3 tests « du jour » de
      l'intégration, rouges connus entre 00:00 et 02:00, à condition d'être rejoués verts après 02:00
- [ ] Chaîne F3 établie et consignée dans le `## Develop log` avant le correctif : depuis l'échec du registre
      jusqu'au 403, avec les fichiers et méthodes traversés. Si la chaîne réelle diffère de celle décrite plus
      haut, le correctif suit la chaîne réelle
- [ ] Les `catch (Exception)` de `GetFoldersAsync` / `ImapFolderService` qui transforment une panne de base en
      `Result.Error` laissent passer les exceptions d'indisponibilité au `GlobalExceptionHandler`. Le task file
      liste chaque `catch` examiné et ce qui en est fait. Les autres catégories d'erreur gardent leur comportement
- [ ] Inventaire dans le task file des autres `catch (Exception)` d'`api-mail` qui rendraient une panne de base
      en 500, avec ce qui en est fait (corrigé ici, ou laissé avec sa raison)
- [ ] **Test d'intégration de bout en bout, `GET /api/v1/mail/folders`, base du praticien indisponible** : la
      réponse réelle est un **503**, `application/problem+json`, extension `code` = `DATABASE_UNAVAILABLE`, sans
      message d'exception brut dans `detail`. Cas nominal : la même route, base disponible, rend 200 et la liste
      des dossiers. Vu rouge sur le code d'avant (500) ou par mutation (règle 1b)
- [ ] **Test d'intégration de bout en bout, route exigeant une boîte (par exemple `GET /api/v1/mail/folders/{folder}`),
      registre indisponible** : la réponse réelle est un **503 `DATABASE_UNAVAILABLE`**, jamais un 403
      `MAILBOX_NOT_ATTACHED` ni `MAILBOX_REQUIRED`. Cas témoin : registre disponible et boîte réellement non
      rattachée, la même route rend toujours **403 `MAILBOX_NOT_ATTACHED`**. Vu rouge sur le code d'avant (403)
      ou par mutation (règle 1b)
- [ ] La façon dont le fixture rend la base ou le registre indisponible est décrite dans le task file. Seul le
      stockage est rendu indisponible, jamais la couche modifiée par la task
- [ ] Tests unitaires : la décision de sélection de boîte quand le registre est indisponible, ≥ 1 test par branche
      (registre indisponible ⇒ indisponibilité ; registre répond « non rattachée » ⇒ 403 inchangé)
- [ ] Trou du filet : la panne de base n'est pas rejouable par `/e2e` (le backend e2e n'injecte pas de saturation
      Postgres). Ligne ajoutée dans `conventions/e2e.md`, section des trous du filet : le bug, pourquoi `/e2e` ne
      l'a pas vu, et le test d'intégration qui le couvre désormais
- [ ] Aucune donnée de santé en clair dans les journaux : les journaux ajoutés ou modifiés ne portent ni adresse
      de boîte complète ni contenu de mail. Les SQLSTATE et les identifiants de corrélation restent
- [ ] Contrat inchangé : aucun fichier de `Dtos/` modifié, aucun frontend touché. Les codes 503 et
      `DATABASE_UNAVAILABLE` existent déjà

## Manual Test Plan

1. **Lancer le backend** : `cd Api/Mail && dotnet run --project src/AppHost`, profil par défaut, avec une boîte
   rattachée.
2. **Cas nominal** : ouvrir la messagerie (`client-blazor` ou `client-mobile`). La liste des dossiers et l'inbox
   s'affichent.
3. **Base indisponible** : arrêter le conteneur PgBouncer, ou Postgres, depuis le tableau de bord Aspire ou par
   `docker stop`, puis rafraîchir l'inbox.
   - Le client affiche « service momentanément indisponible », jamais « messagerie non rattachée » ni l'écran de
     rattachement d'une boîte.
   - Dans Seq, `GET /api/v1/mail/folders` et les routes de la boîte sortent en 503 `DATABASE_UNAVAILABLE`. Aucun
     « Unexpected error getting folders » ni 500.
4. **Retour à la normale** : redémarrer le conteneur. Sans se reconnecter, l'inbox se recharge et la boîte est
   toujours rattachée.
5. **Témoin du 403** : demander une boîte qui n'est pas rattachée au compte (en-tête de boîte d'une autre
   adresse, ou boîte détachée), base disponible. La réponse reste 403 `MAILBOX_NOT_ATTACHED`.
6. **Au banc** (facultatif, skill `loadtest-skill`) : rejouer le palier 1400 de l'escalier de référence. Aucune
   réponse 500 ni 403 n'apparaît dans le journal k6, seulement des 503.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur. Robustesse et conformité interne à la règle 12
- **Exigences DSR honorées** : non applicable. Disponibilité et lisibilité des erreurs du service MSSanté
- **INS** : non applicable. Aucun trait d'identité n'est manipulé
- **Authentification PS** : inchangée (PSC / e-CPS)
- **Habilitations** : **renforcées dans leur lisibilité, inchangées dans leur décision**. Un refus de rattachement
  (403) ne se rend que sur une réponse du registre ; une indisponibilité ne se fait jamais passer pour un refus.
  Aucune boîte n'est ouverte quand le registre ne répond pas (règle 14 : pas d'accès sans verdict)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé. L'échec reste journalisé côté serveur, corrélé par `traceId`. Aucun acte sur une
  boîte n'est ajouté ni retiré ; une requête refusée en 503 n'a pas d'acte à imputer
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui, environnement inchangé
- **AIPD / impact RGPD** : inchangé, aucun traitement nouveau
