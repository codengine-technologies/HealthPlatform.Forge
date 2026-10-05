# todo-task-354.md — Remonter une connexion SMTP / IMAP après un refus du jeton PSC par la messagerie MSSanté

**Repos**: api-mail, client-mobile, client-angular
**Dependencies**: — (aucune)
**Epic**: E013
**Single frontend**: false
**Priorité**: **1** — un envoi de courrier médical échoue sans raison compréhensible, et un nouvel
essai immédiat échoue aussi, à coup sûr. Le praticien ne peut rien faire d'autre qu'attendre deux
à trois minutes sans savoir pourquoi.

> **Origine.** Constaté le 2026-10-05 dans Seq, entre 19:48 et 19:53 UTC (boîte de formation
> `robert.specialiste…@medecin.formation.mssante.fr`).
>
> - Deux envois successifs (`POST /drafts/{id}/send`, 19:48:59 et 19:49:35) sont refusés par le
>   serveur SMTP MSSanté. Il coupe la connexion après le challenge XOAUTH2 et renvoie
>   `{"status":"401","schemes":"bearer","scope":"mail"}` (en base64).
> - Le jeton refusé à 19:48:59 sortait d'un refresh PSC réussi 6 s plus tôt, sans erreur côté proxy.
> - Au second essai, api-mail **n'a même pas appelé le proxy** : il a ressorti de son cache le jeton
>   qu'on venait de lui refuser.
> - Les envois de 19:51:59 et 19:53:39 réussissent, uniquement parce que le cache a expiré entre-temps.
>   La navigation du praticien n'y est pour rien.
> - À la même période, l'opérateur était instable : `MOVE` répondu « Internal error », `AppendToSent`
>   à 8 s, lectures IMAP à 58 s. Un rejet transitoire côté opérateur est plausible, sans pouvoir être
>   prouvé : les logs ne portent aucune claim de jeton, par conception.
>
> Arbitrages de l'humain, le 2026-10-05 :
> - refus persistant après la reprise → **503 réessayable**, brouillon conservé ;
> - **SMTP et IMAP** traités dans la même US ;
> - **fronts mobile et Angular** inclus, avec un message dédié.

## Ce qui existe (constaté dans le code le 2026-10-05)

- **`SmtpConnectionFactory.AuthenticateAsync`** (`Api/Mail/src/Application/Services/Implementation/SmtpConnectionFactory.cs`)
  - Résout le jeton par `IPscTokenProvider.GetAccessTokenAsync`, puis s'authentifie en
    `SaslMechanismOAuth2NoIr`.
  - Le refus MSSanté n'arrive **pas** sous forme d'`AuthenticationException`, mais d'une
    `SmtpProtocolException` (« The SMTP server has unexpectedly disconnected: {base64} »).
  - Il tombe donc dans le `catch` générique (l. 261) → `Result.Error("SMTP connection failed: …")` →
    **502** côté client, sans aucune reprise.
- **`PscTokenProvider`** (`Api/Mail/src/Application/Services/Psc/PscTokenProvider.cs`)
  - Le jeton reste en cache jusqu'à `exp − TokenRefreshMarginSeconds` (30 s).
  - **Aucune API d'éviction** : un jeton que la messagerie vient de refuser est resservi tel quel
    jusqu'à son expiration.
- **`ImapConnectionService`** (`…/ImapConnectionService.cs`, l. 155 et 328-342)
  - Le refus IMAP sort bien en `AuthenticationException`, mais il est converti en
    `Result.Error(...)` **sans éviction ni reprise**.
  - Même défaut, sous une forme voisine : le jeton refusé est resservi à la connexion suivante.

## Objective

Quand la messagerie MSSanté refuse le jeton PSC à l'authentification (SMTP ou IMAP), api-mail
**remonte la connexion lui-même**, une fois, avec un jeton frais. Le praticien ne voit rien quand
la reprise réussit. Quand elle échoue, il voit un message clair, et son brouillon est intact.

1. **Détecter le refus du jeton**, sur les deux protocoles :
   - SMTP : la forme `SmtpProtocolException` + charge base64 `{"status":"401",…}` comme la forme
     `AuthenticationException` ;
   - IMAP : la forme `AuthenticationException` ;
   - seul un **refus du jeton** est concerné. Un échec réseau, TLS ou un timeout garde son traitement
     actuel.
2. **Évincer le jeton refusé** du cache de `PscTokenProvider` (session + sujet, portée RG-L1
   inchangée). Le prochain appel repasse obligatoirement par le proxy.
3. **Une seule reprise** :
   - nouvelle connexion, avec le jeton frais obtenu du proxy ;
   - jamais plus d'une reprise par opération, pour qu'une messagerie qui refuse tout ne provoque pas
     de rafale d'appels au proxy ni à PSC.
4. **Issue de la reprise** :
   - **la reprise réussit** → l'opération aboutit normalement (envoi parti, dossier lu) ;
   - **le proxy déclare la session PSC expirée** → comportement actuel inchangé, **401** « reconnectez-vous » ;
   - **le jeton frais est encore refusé** → **503** `ProblemDetails` (RFC 7807, règle 12) avec un code
     d'erreur dédié (ex. `mail-server-auth-refused`). `detail` : « La messagerie MSSanté a refusé
     la connexion. Réessayez dans quelques instants. » Jamais de 502, jamais le base64 ni le message
     MailKit brut dans le `detail`.
5. **Brouillon conservé** : un envoi refusé ne supprime ni n'altère le brouillon (vérifié par test).
6. **Fronts** (`client-mobile`, `client-angular`) — sur ce 503 d'envoi :
   - message dédié : « La messagerie MSSanté a refusé l'envoi. Votre brouillon est conservé,
     réessayez dans quelques instants. » ;
   - la rédaction reste ouverte avec son contenu ;
   - le bouton Envoyer reste actif pour un nouvel essai ;
   - les autres erreurs d'envoi gardent leur message actuel.

## Hors scope

- **La cause du refus côté opérateur.** Cette US rend api-mail résilient au refus, elle ne
  l'explique pas.
- **Le proxy PSC (`psc-auth-proxy`)** : aucun changement.
- **`client-blazor`** : non listé par arbitrage humain. Il reçoit le même 503 `ProblemDetails`,
  qu'il affiche avec son mapping générique.

## Definition of Done

- [ ] Build passes on every listed repo (0 errors)
- [ ] Tests pass on every listed repo (0 failures, hors rouges pré-existants identifiés sur `develop`)
- [ ] `IPscTokenProvider` expose l'éviction du jeton d'une session. Tests unitaires : l'éviction
      force un nouvel appel au proxy, et l'éviction d'une session ne touche pas une autre session ni
      un autre sujet (RG-L1).
- [ ] SMTP : tests unitaires de la détection du refus. Sont un refus du jeton :
      `SmtpProtocolException` + base64 `status 401`, et `AuthenticationException`. Ne le sont pas :
      une déconnexion sans charge 401, une `SocketException`, un timeout.
- [ ] SMTP : tests unitaires de la reprise :
  - une seule reprise, avec éviction préalable ;
  - jeton frais accepté → succès ;
  - jeton frais refusé → erreur typée 503 ;
  - session PSC expirée → 401 inchangé.
- [ ] IMAP : mêmes tests unitaires de détection et de reprise sur `ImapConnectionService`
- [ ] Test d'intégration de bout en bout pour `POST /api/v1/mail/drafts/{id}/send` (règle 1b), avec
      un serveur SMTP de test qui refuse XOAUTH2 en renvoyant la charge MSSanté réelle (`334` +
      base64 `{"status":"401",…}` puis déconnexion) et un proxy PSC simulé (fournisseur externe) :
  - nominal : le premier jeton est refusé, le second accepté → **200**, message reçu par le serveur
    de test, proxy appelé **exactement 2 fois** ;
  - échec : les deux jetons sont refusés → **503** `application/problem+json`, code d'erreur dédié lu
    dans la réponse, `detail` sans base64 ni message MailKit, proxy appelé exactement 2 fois,
    **brouillon toujours présent en base et inchangé** ;
  - vu rouge par mutation : sans l'éviction, le cas nominal échoue.
- [ ] Test d'intégration de bout en bout pour une route IMAP authentifiée (ex. `GET /api/v1/mail/folders`,
      avec la session IMAP absente du pool), avec un serveur IMAP de test qui refuse XOAUTH2 au
      premier jeton :
  - nominal → 200 et dossiers lus ;
  - échec (deux refus) → 503 `ProblemDetails` ;
  - vu rouge par mutation.
- [ ] `/send` ne répond plus jamais **502** sur un refus du jeton (assertion explicite dans le test
      d'intégration d'échec).
- [ ] client-mobile : test de composant de la rédaction sur le 503 d'envoi : message dédié affiché,
      contenu conservé, bouton Envoyer actif. Une autre erreur garde son message actuel.
- [ ] client-angular : même test de composant
- [ ] `data-testid` sur le message d'erreur d'envoi (mobile et Angular)
- [ ] Scénario **E2E-COMPOSE-003** v1 ajouté dans `Api/Mail/e2e/scenarios.yml` et implémenté dans
      chaque client où il est requis (`mobile: requis`, `angular: requis`). Titre : « Un envoi refusé
      par la messagerie laisse le brouillon intact et peut être renvoyé ». Le profil e2e doit
      pouvoir simuler le refus de l'opérateur au premier envoi : moyen technique au choix de
      `/develop`, sinon `questions/task-354.md`.
- [ ] Trou du filet : E2E-COMPOSE-003 prouvé rouge sur le bug non corrigé (envoi en échec générique),
      ligne ajoutée dans `conventions/e2e.md`.
- [ ] Évènements PGSSI-S journalisés :
  - refus du jeton par la messagerie (protocole, boîte, horodatage) ;
  - reprise tentée, et son issue (succès / échec) ;
  - via le journal d'audit existant (`AuditActionType`). Si un membre est ajouté, mettre à jour le
    miroir TS de `client-angular` (valeur explicite).
- [ ] Aucune donnée de santé en clair dans les logs, et **aucun jeton** : ni le jeton PSC, ni la
      charge base64 renvoyée par le serveur ne sont journalisés en entier. Le statut décodé seul est
      autorisé.

## Manual Test Plan

- **Lancer le backend** : `cd Api/Mail && dotnet run --project src/AppHost` (profil standard,
  boîte de formation MSSanté connectée par PSC).
- **Lancer le mobile** : `cd Client/Mobile && npm start` → http://localhost:4200, connexion PSC.
- **Lancer Angular** : `cd Client/Angular/front && npm start`, module MSS, connexion PSC.
- **Cas nominal (reprise invisible)** :
  1. Dans Seq, repérer l'expiration du jeton en cours. Ou, en local, forcer un refus au premier
     essai par la bascule de test fournie par `/develop` (documentée dans le `## Develop log`).
  2. Rédiger un message à soi-même et l'envoyer.
  3. Attendu : le message part et arrive dans la boîte de réception. Dans Seq, on voit un refus du
     jeton, une reprise, puis « Email sent successfully ». Aucune erreur à l'écran.
- **Cas d'échec (refus persistant)** :
  1. Forcer le refus des deux jetons (même bascule de test), puis envoyer.
  2. Attendu sur mobile et sur Angular : le message « La messagerie MSSanté a refusé l'envoi. Votre
     brouillon est conservé, réessayez dans quelques instants. »
  3. La rédaction reste ouverte avec son contenu, et le brouillon figure dans Brouillons.
  4. Lever la bascule, renvoyer : le message part.
- **IMAP** : forcer le refus au premier jeton, attendre la fin de la session IMAP (5 min) ou
  redémarrer l'API, puis ouvrir la boîte de réception. Attendu : les dossiers s'affichent, et Seq
  montre une reprise.
- **Contrôle des logs** : dans Seq, ni jeton, ni base64 complet, ni contenu de message sur ces
  évènements.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur. Robustesse technique d'un flux existant, aucune nouvelle
  fonctionnalité référencée.
- **Exigences DSR honorées** : non applicable, aucune exigence nouvelle. Les exigences MSSanté
  existantes sont conservées à l'identique :
  - authentification XOAUTH2 par jeton PSC ;
  - TLS conforme ANS (`TlsCipherSuiteValidator`) ;
  - contrôle de révocation OCSP/CRL.
- **INS** : non applicable. La reprise de connexion ne lit ni ne transmet d'identité patient.
  L'INS éventuellement présente dans les en-têtes du message envoyé est inchangée.
- **Authentification PS** : PSC (e-CPS), niveau eIDAS substantiel, inchangé. La reprise utilise
  **exclusivement** un jeton PSC frais obtenu du proxy. Aucun repli vers un mot de passe, aucune
  réutilisation d'un jeton refusé.
- **Habilitations** : inchangées. La liaison session ↔ sujet Keycloak (RG-L1) s'applique aussi à
  l'éviction.
- **Interop CI-SIS** : non applicable. Transport MSSanté existant, aucun document produit ou
  modifié.
- **Tracé PGSSI-S** : refus d'authentification par la messagerie, reprise tentée, et issue de la
  reprise. Journal d'audit en base, durée de conservation du journal d'audit existant (inchangée).
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui. Environnement de la plateforme inchangé, aucune nouvelle donnée stockée.
- **AIPD / impact RGPD** : inchangé. Aucun nouveau traitement : les évènements tracés sont des
  évènements d'authentification déjà couverts par le journal d'audit.
