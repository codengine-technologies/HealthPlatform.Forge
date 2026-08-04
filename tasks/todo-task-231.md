# todo-task-231.md — Chaque envoi paie une connexion SMTP neuve (TLS + OCSP + AUTH) : réutiliser la connexion et construire le MIME avant de se connecter

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-216 (todo — retrait de la voie d'écriture IMAP task-213) :
**coordination obligatoire**, les deux tasks touchent le chemin d'envoi/archivage ;
celle-ci ne touche que la jambe SMTP et ne dépend pas de l'issue de task-216.
**Priorité**: **2** — `send` est hors grille SLO (p50 1 340 ms) et pèse 13,4 %
du temps serveur. Coût fixe par appel, indépendant de la charge.

> ⚠️ **Contrainte absolue — aucun impact frontend.** Même route
> (`POST Mail/sendmail`), même corps de réponse — notamment le champ
> `archived`/`warning` (sémantique anti-renvoi de document posée par
> task-223) reste **décidable au moment de l'acquittement** : l'archivage
> IMAP reste synchrone dans cette task. Le différer serait un changement de
> contrat → hors périmètre, décision produit séparée si besoin.

## Objective

Réduire le coût fixe de l'acquittement d'envoi en s'attaquant à ce que
l'analyse de code a établi comme postes évitables — sans toucher à l'ordre
métier (SMTP puis archivage) ni au contrat :

1. **Connexion SMTP jetable à chaque envoi** : `SmtpConnectionFactory` fait
   `new SmtpClient()` → CONNECT → TLS avec **vérification de révocation
   OCSP/CRL du certificat** → AUTH, puis `DisconnectAsync(true)` (QUIT) à la
   fin — **aucun pool**, contrairement à IMAP qui réutilise la connexion de
   session. C'est le poste dominant du coût fixe.
2. **Le MIME est construit après la connexion**, avec **2 lectures base sous
   session SMTP ouverte** (identité expéditeur via `GetSettingsAsync`,
   signature par défaut via `GetDefaultAsync`) : la connexion authentifiée
   est tenue inutilement pendant ces I/O.
3. La jambe IMAP (`AppendToSent` : SELECT + APPEND + CLOSE, ~2,3 s de
   détention p95 sur sa voie d'écriture dédiée, attente nulle) bénéficie déjà
   de la réutilisation de connexion après le premier envoi — le gain est
   côté SMTP.

## Remèdes demandés

1. **Réutiliser la connexion SMTP** au sein de la session praticien (même
   patron que le pool IMAP par session) : le CONNECT + TLS + OCSP + AUTH ne
   se paie qu'au premier envoi, les suivants font DATA (+ NOOP de validation
   de fraîcheur). Gestion propre : détection de connexion morte → reconnexion
   transparente ; fermeture au nettoyage de session (même cycle de vie que
   les clients IMAP de session).
2. **Construire le MIME avant d'ouvrir/emprunter la connexion** : les
   lectures base (identité, signature) se font hors session SMTP tenue ; les
   settings sont déjà cachés Redis 5 min — utiliser ce cache tel quel.
3. **Compter les allers-retours SMTP** dans `MailServerSolicitationRecorder`
   (aujourd'hui câblé sur IMAP uniquement) — la métrique de task-225 devient
   complète et la contre-épreuve lisible.

**Hors périmètre (décisions explicites)** : archivage différé (contrat
`archived`), désactivation du contrôle de révocation OCSP/CRL (exigence de
confiance MSSanté/IGC Santé — on ne détend pas la vérification de
certificat, on amortit son coût par la réutilisation de connexion).

## La mesure — tirs `journey-mssante-n300` du 2026-08-04

| Signal | Valeur (tir 17:05) |
|---|---|
| `send` p50 / p95 (palier 300) | 1 340 / 2 063 ms — hors grille SLO, **plat sur les 3 paliers** (coût fixe) |
| Part du temps serveur | 13,4 % (4 502 s, 2 853 appels) |
| Verrou `AppendToSent` (voie d'écriture) | attente 0,005 s / détention 2,322 s p95 — le coût est le travail, pas la contention |
| Route serveur `sendmail` p95 max | 5 250 ms |

Décomposition établie par l'analyse de code : validation + garde opposition
patient (1 requête/destinataire INS) → **connexion SMTP complète** → MIME
(2 lectures base sous connexion) → DATA → QUIT → archivage IMAP (3 RTT) →
réponse. Sous latence injectée, la jambe « connexion + handshake » est
l'essentiel de l'écart entre 1 340 ms observés et le plancher DATA + APPEND.

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] **Zéro changement de contrat** : route, code HTTP, corps de réponse (`queued`/`archived`/`warning`) identiques — tests d'intégration existants inchangés ; l'archivage reste synchrone
- [ ] Connexion SMTP réutilisée au sein de la session : unit tests — 2e envoi sans CONNECT/AUTH, reconnexion transparente sur connexion morte, fermeture au nettoyage de session, pas de fuite de client SMTP (dispose vérifié)
- [ ] MIME construit avant l'emprunt de la connexion — unit test d'ordre d'appels (mock : aucune I/O base entre CONNECT et DATA)
- [ ] La vérification de révocation du certificat serveur reste active (aucune option de validation détendue) — assertion dans les tests de la factory
- [ ] Allers-retours SMTP comptés dans `MailServerSolicitationRecorder`
- [ ] Aucune donnée de santé en clair dans les logs (les logs de connexion SMTP ne portent ni sujet ni contenu ni INS)
- [ ] **Contre-épreuve au banc (bloquante pour le merge, pas pour la PR)** : tir `journey` n300 iso-conditions avant/après :
  - `send` p50 en **nette baisse** (référence : 1 340 ms ; attendu : plancher DATA + APPEND, ordre de grandeur ≤ 800 ms)
  - part de `send` dans le temps serveur en baisse (référence : 13,4 %)
  - 0 erreur d'envoi, vérification par base PASS (les messages envoyés arrivent, complétude tenue)
  - compteur de sollicitations SMTP : ~1 connexion par session et non plus ~1 par envoi

## Manual Test Plan

- Monter le banc : skill `loadtest-skill`
- Tir de contre-épreuve : `journey`, 300 médecins, latence `mssante`,
  iso-conditions avec `journey-mssante-n300-170512`
- Comparer : latence étape 6 « Envoi (acquittement UI) », part de `send` dans
  les axes d'amélioration
- Contrôle fonctionnel : envoyer 2 messages successifs depuis la même session
  → le second est nettement plus rapide ; vérifier la copie dans Envoyés
  (`archived: true`) pour les deux
- Contrôle de panne : couper le serveur SMTP entre deux envois → le second
  reconnecte de façon transparente ou rend l'erreur habituelle (jamais un
  faux succès)

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — optimisation interne
- **Exigences DSR honorées** : non applicable — pas de changement fonctionnel ; l'exigence de vérification des certificats IGC Santé est explicitement **préservée** (DOD)
- **INS** : non applicable — la garde d'opposition patient est inchangée
- **Authentification PS** : inchangée
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable — en-têtes et corps MSSanté inchangés (même code de construction MIME, seul le moment change)
- **MSSanté** : la connexion réutilisée reste authentifiée par le même compte/certificat que la connexion jetable ; la vérification de révocation reste active à l'établissement
- **Tracé PGSSI-S** : inchangé — la trace d'envoi et la trace d'archivage (`MailArchiveSent`) sont conservées à l'identique
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : inchangé
