# todo-task-425.md — Panne de la messagerie MSSanté en cours de lecture : le médecin reçoit « messagerie momentanément injoignable » (503), jamais une erreur inattendue (500)

**Repos**: api-mail
**Dependencies**: — (aucune ; task-423 a établi que ces 500 ne viennent pas de la base)
**Epic**: E015
**Single frontend**: true
**Priorité**: **2**. Sous charge, des milliers de lectures rendent un 500 « An unexpected error occurred » au lieu
d'un 503 qui dit au médecin que sa messagerie est momentanément injoignable. Règle 12.

> **Origine.** Campagne « limites » du 2026-11-05, itération 1 (escalier `journey`, IA simulée), palier 1400.
> Rapport : `Api/Mail/tests/loadtest-k6/reports/2026-11-05/report-journey-escalier-1996-20261104-ia-simulee-013324.md`.
> Écartée de task-423 par décision humaine du 2026-11-05 : l'analyse du code a montré que les `catch` de ces routes
> n'enveloppent **aucun** appel à la base. Voir `questions/task-423.md` et le `## Develop log` de task-423.

## Ce qui est établi

| Route | 500 au palier 1400 (journal k6, première occurrence par médecin et par geste) | `catch` qui rend le 500 |
|---|---|---|
| `GET /api/v1/mail/folders/{folder}` | 3 841 | `ImapService.ReadFolderAsync` → `MapFolderAccessExceptionAsync`, branche `default` |
| `GET /api/v1/mail/folders/{folder}/emails/today` | 108 | `ImapService.ReadTodayAsync` → `MapFolderAccessExceptionAsync`, branche `default` |
| `GET /api/v1/mail/folders/{folder}/emails/content/{uid}` | 135 | `ImapService.GetEmailContentInternalAsync`, lecture du message ; rend `Result.Error(ex.Message)` |

- Le `try` de ces `catch` ne fait que de l'IMAP : connexion, verrou de session (en mémoire), `STATUS`, `SEARCH`,
  `FETCH`, lecture des parties. Une panne IMAP **survenue après la connexion** (session coupée, délai dépassé, réponse
  `NO`/`BAD`) y est attrapée et rendue en 500 générique.
- Au même palier, 5 931 réponses étaient déjà des **503** « Impossible de joindre le serveur de messagerie » : la
  panne **à la connexion** est bien classée. C'est la panne **en cours de lecture** qui ne l'est pas.
- **Cause exacte à confirmer par la trace avant tout correctif** (consigne « Filtre d'exception » de
  `conventions/csharp.md`) : Seq était injoignable lors de task-423. Le type d'exception attrapé (MailKit
  `ImapProtocolException`, `IOException`, `ServiceNotConnectedException`, délai…) décide du correctif.

## Objective

Une panne de la messagerie MSSanté survenue pendant la lecture d'un dossier, de « aujourd'hui » ou du contenu d'un mail
rend un **503 `MAIL_SERVER_UNAVAILABLE`** (`application/problem+json`, règle 12), comme la panne à la connexion. Jamais
un 500 générique, jamais le message brut de l'exception dans `detail`.

Règles :
- **Classement par type d'exception**, jamais par le texte du message. Les familles « transport / session IMAP »
  deviennent une indisponibilité. Les autres erreurs gardent leur comportement (un dossier disparu reste un 404
  `FOLDER_NOT_FOUND`, task-352).
- **Une session morte reste rejouée une fois** avant d'être déclarée indisponible (task-277, `DeadSessionPolicy`).
- **Zéro fuite** : le `detail` ne porte ni message d'exception, ni nom de dossier, ni adresse de boîte. Le contenu de
  mail rend aujourd'hui `Result.Error(ex.Message)`, à fermer.

### Hors périmètre

- Les pannes de base : task-423. Le seuil de connexions Postgres : task-422.
- Les clients : ils lisent déjà le 503 `MAIL_SERVER_UNAVAILABLE`. Aucun écran ne change.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`
- [ ] Cause établie et consignée dans le `## Develop log` avant le correctif : types d'exception attrapés sur les trois
      routes, relevés dans Seq lors d'un tir ou d'une panne provoquée, avec leur pile
- [ ] **Test d'intégration de bout en bout, `GET /api/v1/mail/folders/{folder}`, IMAP coupé en cours de lecture** :
      503, `code` = `MAIL_SERVER_UNAVAILABLE`, `detail` fixe. Cas nominal : 200 et la liste. Vu rouge (500) sur le code
      d'avant ou par mutation (règle 1b)
- [ ] Même test pour `GET …/emails/today` et pour `GET …/emails/content/{uid}` (message déposé au préalable)
- [ ] Le serveur IMAP est le seul élément rendu défaillant (fournisseur externe, règle 1b) : la manière (interruption de
      Dovecot, enveloppe de client IMAP du banc d'intégration, proxy) est décrite dans le task file
- [ ] Tests unitaires du classement : une exception de transport → indisponibilité ; un dossier disparu → 404 inchangé ;
      une autre erreur → comportement inchangé
- [ ] Trou du filet : ligne ajoutée dans `conventions/e2e.md` (panne IMAP en cours de lecture non rejouable par `/e2e`)
- [ ] Aucune donnée de santé ni nom de dossier dans les journaux ajoutés ou modifiés
- [ ] Contrat inchangé : aucun fichier `Dtos/`, aucun frontend ; le code `MAIL_SERVER_UNAVAILABLE` existe déjà

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost`, profil par défaut, une boîte rattachée.
2. Ouvrir l'inbox (`client-blazor` ou `client-mobile`) : la liste s'affiche.
3. Pendant l'ouverture d'un dossier, arrêter le conteneur Dovecot (tableau de bord Aspire ou `docker stop`) : le client
   affiche « messagerie momentanément injoignable », jamais « erreur inattendue ». Dans Seq, la route sort en 503
   `MAIL_SERVER_UNAVAILABLE`.
4. Redémarrer Dovecot : sans se reconnecter, l'inbox se recharge.
5. Supprimer un dossier depuis un autre client IMAP puis l'ouvrir : toujours 404 « le dossier n'existe plus »
   (task-352, inchangé).
6. Au banc (facultatif, skill `loadtest-skill`) : rejouer le palier 1400 de l'escalier de référence ; plus de 500 sur ces
   trois routes.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur. Robustesse et conformité interne à la règle 12
- **Exigences DSR honorées** : non applicable. Lisibilité des erreurs du service MSSanté
- **INS** : non applicable. Aucun trait d'identité n'est manipulé
- **Authentification PS** : inchangée (PSC / e-CPS)
- **Habilitations** : inchangées. Aucune action sur une boîte n'est ajoutée ni retirée (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé. L'échec reste journalisé côté serveur, corrélé par `traceId`
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui, environnement inchangé
- **AIPD / impact RGPD** : inchangé, aucun traitement nouveau
