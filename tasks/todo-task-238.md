# todo-task-238.md — Envoi sous 1 000 ms : la connexion SMTP retenue meurt entre deux envois — l'entretenir (keep-alive), sonder moins, amortir l'OCSP

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune (task-231 mergée — elle a posé la réutilisation de
connexion que cette task rend effective). **Coordination** avec task-216 (todo,
voie d'écriture IMAP) : sans objet tant que l'archivage reste synchrone et hors
périmètre ici, mais si les deux passent en wip en même temps, séquencer.
**Priorité**: **1** — `send` est la seule étape 🔴 de la certification du
2026-08-06 : hors grille SLO (p50 1 227-1 229 ms, cible 1 000) **et** premier
poste hors lecture du temps serveur (17,9 %). Coût fixe par appel, plat de 50 à
200 médecins.

> ⚠️ **Contrainte absolue — aucun impact frontend, aucun changement de
> contrat.** Même route (`POST Mail/sendmail`), même code HTTP, même corps de
> réponse. Le champ `archived`/`warning` (sémantique anti-renvoi de document,
> task-223) reste **décidé au moment de l'acquittement** : l'archivage IMAP
> reste **synchrone**, conformément à la décision produit gravée par task-231.

## Objective

task-231 a mis en place la réutilisation de la connexion SMTP par session — et
la certification du 2026-08-06 mesure que **le bénéfice ne se réalise pas au
rythme réel** : entre deux envois d'un même praticien (plusieurs minutes),
la connexion retenue dépasse le délai d'inactivité du serveur et meurt. La
sonde de fraîcheur la trouve morte à l'emprunt, et chaque envoi repaie
CONNECT + TLS + validation de suite + **OCSP/CRL** + AUTH. Trois postes
évitables, établis par l'analyse de code du 2026-08-06 :

1. **Aucun keep-alive SMTP.** La boucle NOOP de session (30 s) n'entretient
   que le client IMAP (`MailClientSession.StartKeepAlive`) ; rien ne maintient
   `_smtpClient` en vie. La session sait déjà faire — le SMTP n'est pas branché.
2. **La sonde de fraîcheur coûte un aller-retour à chaque emprunt**, même
   quand la connexion vient de servir. Sous latence, elle produit en outre des
   `IOException` de bruit (1 345 sur le tir du 2026-08-06).
3. **La vérification de révocation OCSP/CRL est repayée à chaque
   reconnexion** — aucune mise en cache des réponses de révocation, alors
   qu'une réponse OCSP est conçue pour être réutilisée jusqu'à son
   `nextUpdate`.

## Remèdes demandés

1. **Keep-alive SMTP** : étendre la boucle d'entretien de session existante au
   client SMTP retenu (NOOP périodique sous le verrou `smtp_session`, même
   patron non-bloquant que la boucle IMAP). La rétention ne change pas de
   politique : la connexion vit et meurt avec la session praticien
   (expiration d'inactivité 5 min, fermeture polie au nettoyage) — le
   keep-alive la garde **saine** pendant cette fenêtre, il n'en retient pas
   davantage (contrainte opérateur MSSanté « connexions par boîte » inchangée).
2. **Sonde conditionnée à l'âge** : pas de NOOP de fraîcheur si la connexion a
   servi (ou a été entretenue) il y a moins de N secondes (N aligné sur la
   cadence du keep-alive). Le NOOP par emprunt disparaît du chemin nominal.
3. **Cache des réponses de révocation OCSP/CRL** par (émetteur, numéro de
   série), borné par la validité de la réponse (`nextUpdate`), pour amortir
   les reconnexions résiduelles (première connexion de session, reprise après
   coupure). **La vérification reste active** : on met en cache la réponse
   signée dans sa période de validité, on ne détend jamais le contrôle
   (exigence de confiance MSSanté/IGC Santé, décision task-231 reconduite).

**Hors périmètre (décisions explicites)** :
- **Archivage différé** (`AppendToSent` asynchrone via la file de fond) :
  changement de contrat `archived` → décision produit séparée. **Porte de
  sortie** : si la contre-épreuve au banc montre `send` p50 encore > 1 000 ms
  avec les trois remèdes, ouvrir une US dédiée (sémantique d'acquittement à
  redéfinir : `archived` différé + notification).
- **`MdnService`** (accusés MDN en connexion jetable) : volume marginal, à
  traiter opportunément dans une US d'entretien.
- Toute désactivation ou détente de la validation de certificat.

## La mesure — certification `journey-certif-n200-022915` du 2026-08-06

| Signal | Valeur |
|---|---|
| `send` p50 / p95 (palier 200) | 1 229 / 1 907 ms — hors grille (cible 1 000 / 3 000), **plat sur les 3 paliers** |
| Part du temps serveur | 17,9 % (2 434 s, 1 659 appels) — 2e poste, 1er hors lecture |
| Verrou `AppendToSent` (voie d'écriture) | attente 0,107 s / détention 2,369 s p95 |
| `IOException` sondes de fraîcheur | 1 345 sur le tir |
| Sessions IMAP/SMTP au rythme réel | ~2 par médecin — la connexion retenue meurt entre deux envois |

Référence de comparaison : re-certification n200 post-fix harnais génération 0
(voir `Api/Mail/tests/loadtest-k6/reports/INDEX.md`, note du 2026-08-06) si
elle a eu lieu, sinon `journey-certif-n200-022915`.

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] **Zéro changement de contrat** : route, code HTTP, corps de réponse
      (`queued`/`archived`/`warning`) identiques — tests d'intégration
      existants inchangés ; l'archivage reste synchrone
- [ ] Keep-alive SMTP : unit tests — le NOOP périodique entretient le client
      SMTP retenu ; il ne bloque jamais un envoi en cours (patron `Wait(0)`) ;
      il s'arrête à l'expiration/nettoyage de session ; aucune connexion
      retenue au-delà du cycle de vie de session existant
- [ ] Sonde conditionnée : unit tests — pas de NOOP si dernier usage < N s ;
      NOOP (puis reconnexion transparente) au-delà ; N configurable avec
      défaut documenté
- [ ] Cache OCSP/CRL : unit tests — réponse réutilisée dans sa validité,
      re-validation après `nextUpdate`, jamais de bypass quand le cache est
      vide ou la réponse expirée ; la vérification de révocation reste active
      (assertion existante de task-231 conservée)
- [ ] Envois concurrents de la même session sérialisés proprement sous
      `smtp_session` avec le keep-alive actif (pas de course NOOP/DATA)
- [ ] Aucune donnée de santé en clair dans les logs (keep-alive, sonde et
      cache ne journalisent ni sujet, ni contenu, ni INS, ni RPPS)
- [ ] **Contre-épreuve au banc (bloquante pour le merge, pas pour la PR)** :
      tir `journey` n200 K=1 iso-conditions avant/après :
  - `send` p50 **≤ 1 000 ms** (référence 1 229 ms) — l'étape 6 passe la grille
  - part de `send` dans le temps serveur en nette baisse (référence 17,9 %)
  - `IOException` de sonde en forte baisse (référence 1 345)
  - 0 erreur d'envoi, vérification par base PASS, `archived: true` sur les
    envois vérifiés
  - sollicitations SMTP : ~1 connexion par session soutenue au rythme réel
    (et non plus ~1 par envoi)

## Manual Test Plan

- Monter le banc : skill `loadtest-skill` (AppHost profil loadtest, latence
  `mssante`)
- Tir de contre-épreuve : `journey`, 200 médecins, K=1, iso-conditions avec la
  référence (même seed 500×247, maildir vierge, mêmes paliers 50/100/200 × 32
  min)
- Comparer dans le rapport : étape 6 « Envoi (acquittement UI) » (p50/p95 par
  palier), part de `send` dans « Axes d'amélioration », familles d'exceptions
  Seq (`IOException` sondes)
- Contrôle fonctionnel local : envoyer 2 messages à > 5 min d'intervalle
  depuis la même session → le second ne repaie pas la connexion (logs : pas de
  CONNECT/AUTH) ; vérifier la copie dans Envoyés (`archived: true`) pour les
  deux
- Contrôle de panne : couper le serveur SMTP entre deux envois → reconnexion
  transparente, l'envoi suivant aboutit ; aucune fuite de client
- Contrôle de confiance : certificat serveur révoqué/inconnu → l'envoi est
  refusé exactement comme avant (le cache n'a pas détendu la validation)

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — optimisation de performance sans changement
  fonctionnel ni de contrat
- **Exigences DSR honorées** : non applicable — aucune exigence nouvelle ; les
  exigences MSSanté existantes (transport, certificats) sont reconduites à
  l'identique
- **INS** : non applicable — la garde d'opposition patient à l'envoi est
  inchangée ; aucun traitement d'INS ajouté
- **Authentification PS** : inchangée (PSC/e-CPS en amont, XOAUTH2 vers
  l'opérateur MSSanté) — la task ne touche pas à l'authentification
- **Habilitations** : non applicable — aucun changement
- **Interop CI-SIS** : non applicable — transport MSSanté SMTP inchangé ;
  **IGC Santé** : la vérification de révocation OCSP/CRL des certificats
  serveur reste active, seule la réponse signée est mise en cache dans sa
  période de validité (`nextUpdate`)
- **Tracé PGSSI-S** : évènements d'envoi inchangés ; les échecs de
  keep-alive/reconnexion sont journalisés côté serveur sans donnée de santé —
  durées de conservation inchangées
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé, aucune donnée nouvelle
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau, aucune donnée
  nouvelle (le cache OCSP ne porte que des identifiants de certificats
  serveur)
