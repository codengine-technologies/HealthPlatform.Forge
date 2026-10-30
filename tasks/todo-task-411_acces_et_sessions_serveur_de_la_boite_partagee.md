# todo-task-411 — Accès et sessions serveur de la boîte partagée

**Repos**: api-mail
**Dependencies**: task-407 (les branches touchent les mêmes services d'envoi et de session ; à démarrer après son merge)
**Epic**: E020

> **Origine** : audit du périmètre « boîte déléguée » du 2026-10-30
> (`Docs/audits/2026-10-30-audit-boite-deleguee.md`). Constats M2, M3, M4, M12 et les mineurs
> sessions et synchronisation.
>
> **Single layer** : backend seul. Le comportement visible ne change que par la fermeture d'accès
> due, déjà rendue par l'écran « accès suspendu » (task-403).

## Objectif

Quand un délégataire perd l'accès à une boîte, plus rien ne lui parvient et plus rien n'est fait en
son nom. Un acte n'emprunte jamais l'authentification IMAP d'une autre personne. La vérification
d'accès n'échoue jamais en position ouverte, et n'épuise pas l'opérateur.

## Règles

1. **Connexion IMAP de fond par personne** (M2). Le pool des connexions de fond
   (`BackgroundImapConnectionRegistry`) est indexé par **boîte et personne**
   (`AuthenticationSubject`), jamais par la boîte seule. Une synchro lancée par une personne
   n'utilise que sa propre connexion, authentifiée avec son jeton PSC.
2. **Détacher, suspendre ou se déconnecter coupe tout** :
   - la connexion de fond de la personne est évincée ;
   - ses sessions IMAP et SMTP de premier plan sont fermées ;
   - la synchro qu'elle a lancée est arrêtée ;
   - son verdict d'opérateur est révoqué.

   Cela vaut pour la suspension par le verrou, le détachement et la déconnexion. Les sessions des
   autres personnes de la boîte ne sont pas touchées.
3. **Flux temps réel : échec fermé** (M3). Toute exception de la revérification d'accès d'un flux
   SSE ferme le flux, après avoir poussé l'événement d'accès suspendu quand c'est possible. La
   sonde de l'opérateur attrape et classe toutes ses erreurs (`UnavailableException`, conflit
   d'identité PSC) : un « injoignable » ne prolonge jamais l'accès au-delà du verdict.
4. **Routes de diagnostic retirées** (M4, décision humaine du 2026-10-30). Le contrôleur
   `AiDiagnosticsController` est supprimé, ainsi que le code qui ne sert qu'à lui. Le reste est
   conservé et vérifié par la recherche des usages. Les tests et la doc qui le citent suivent.
5. **Sonde de l'opérateur** (M12) :
   - un jeton PSC refusé est évincé, puis la sonde est rejouée **une fois** avant de conclure au
     refus, comme sur le chemin des requêtes (task-354) ;
   - le renouvellement d'un verdict expiré est **unique** par (personne, boîte) : les requêtes
     concurrentes attendent le même résultat ;
   - une connexion IMAP réutilisée et toujours authentifiée renouvelle le verdict.
6. **Clés et quotas** :
   - la clé du pool de sessions de premier plan porte la personne. Le commentaire « l'e-mail vient
     de la claim mssEmail » est corrigé ;
   - `psc:person-name:{…}` est indexé par un **condensat** de la session du proxy, jamais par le
     cookie en clair ;
   - `MaxSessionsPerMailbox` s'applique **par personne** sur la boîte ;
   - pause et reprise de synchro n'agissent que sur la synchro de la personne qui les demande.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Unit tests :
  - registre des connexions de fond, avec deux personnes sur une boîte et deux entrées ;
  - éviction de la connexion d'une personne ;
  - classement de toutes les erreurs de sonde ;
  - appel unique au renouvellement ;
  - rejeu d'un jeton refusé ;
  - condensat de la clé `psc:person-name`.
- [ ] Test d'intégration de bout en bout, **deux personnes sur la même boîte** : le délégataire
      lance la synchro, puis l'opérateur le refuse. La synchro suivante du titulaire s'authentifie
      avec le jeton du titulaire, ce qu'on lit dans le serveur IMAP du banc (identité de la session
      Dovecot) et dans la trace. Vu rouge (règle 1b).
- [ ] Test d'intégration de bout en bout pour le flux `GET …/events` : la revérification lève une
      exception, et le flux se ferme (le client lit la fin du flux, précédée de `access-suspended`).
      Vu rouge.
- [ ] Test d'intégration de bout en bout pour le détachement : le délégataire détache la boîte
      pendant sa synchro. La synchro s'arrête, sa connexion est fermée, et aucune trace postérieure
      ne porte son nom. Vu rouge.
- [ ] Test d'intégration de bout en bout pour le verrou : dix requêtes concurrentes à l'expiration
      du verdict ne lancent qu'une seule sonde de l'opérateur (compteur de sondes du banc). Vu rouge.
- [ ] Test d'intégration : `/api/v1/diagnostics/*` répond 404, et le code supprimé n'a plus aucun
      usage (`git grep` consigné)
- [ ] Aucune donnée de santé en clair dans les logs. Aucun cookie de session en clair dans Redis.
- [ ] Évènements PGSSI-S journalisés : suspension, détachement et fin de session au nom de la
      personne (inchangés, à vérifier)

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil e2e), avec l'opérateur simulé
  du banc (`POST /api/v1/testing/operator-refusals`).
- Titulaire et délégataire e2e sur `boite-praticien`.
- Le délégataire ouvre la boîte (la synchro démarre), puis l'opérateur simulé le refuse.
- Attendu :
  - l'écran du délégataire passe à « accès suspendu » sous cinq minutes ;
  - le flux temps réel s'arrête ;
  - dans Seq, les synchros suivantes du titulaire sont au nom du titulaire.
- Couper le proxy PSC 30 secondes pendant qu'un délégataire a la boîte ouverte. Attendu : le flux se
  ferme, sans continuer en silence.
- Appeler `GET /api/v1/diagnostics/check-embeddings-status`. Attendu : 404.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — sécurité de la délégation
- **Exigences DSR honorées** : référentiel socle MSSanté #2 (clients), ECO.1.2.8 (le délégataire se
  connecte avec son propre jeton PSC). PGSSI-S : fin d'accès effective à la révocation.
- **INS** : non applicable — aucune donnée patient nouvelle
- **Authentification PS** : PSC. Chaque connexion IMAP utilise le jeton de la personne qui agit.
- **Habilitations** : délégataire et membre, sous verdict récent de l'opérateur (règle 14). Le
  titulaire reste exempté (décision humaine du 2026-10-30, M10 inchangé).
- **Interop CI-SIS** : non applicable — IMAP et SMTP MSSanté seulement
- **Tracé PGSSI-S** : suspension, détachement, fin de session ; conservation 3 653 jours
  (`HealthDataAccess`)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — plateforme
- **AIPD / impact RGPD** : inchangé. Le retrait des routes de diagnostic réduit l'exposition.
