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


## Branches

- `api-mail` (pushed) : `fix/task-238-smtp-keepalive-sonde-ocsp` —
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-238-smtp-keepalive-sonde-ocsp
- `dtos-mss` (pushed) : même nom — **auto-incluse**, aucun changement de contrat attendu
  (contrainte absolue de la US) ; si vide, aucune PR, suppression manuelle au merge
  (7e occurrence attendue du défaut de cycle).

Pré-flight vert sur les six repos mesurables. Dépendances : task-231 mergée. Coordination
task-216 : sans objet (archivage synchrone, hors périmètre ici, task-216 encore en todo).

⚠️ Contexte plateforme au moment du /start : GitHub Actions ne consomme plus les événements
du repo depuis 13:56Z — la CI de la PR pourrait ne pas se déclencher (précédent : PR #167,
mergée par l'humain sans verdict CI, en connaissance de cause).


## Develop log

Commit `f40cfe6` sur `fix/task-238-smtp-keepalive-sonde-ocsp`.

### Remède 1 — le keep-alive SMTP

La boucle d'entretien de session (30 s) couvre désormais le client SMTP retenu, même patron
non bloquant que la voie IMAP (`Wait(0)` : si le verrou est pris, la connexion sert — un
envoi n'attend **jamais** derrière un battement). Deux renforts au passage :

- **un NOOP d'entretien qui échoue écarte le client sur-le-champ** (fermeture sans I/O, sous
  le verrou déjà détenu) — le prochain emprunt reconnecte proprement au lieu de payer
  l'`IOException` de sonde (1 345 sur le tir de référence) ;
- **le démarrage devient idempotent et bi-voie** : l'adoption d'un client SMTP lance la
  boucle — avant, seul le getter IMAP le faisait, et une session qui n'avait jamais lu
  n'entretenait pas son SMTP.

### Remède 2 — la sonde conditionnée à l'âge

La session tient un **signal de santé** (adoption, NOOP d'entretien réussi, sonde réussie) —
distinct de l'accès, et il le faut : l'accès est rafraîchi **à l'emprunt**, avant qu'on sache
si la connexion vit ; s'en servir rendrait la sonde inatteignable. L'emprunt réutilise sans
sonder si le signal a moins de `SmtpProbeMaxAge` (défaut **60 s** = 2 × la cadence du
keep-alive, configurable par domaine ; zéro/négatif = sonder à chaque emprunt — le repli
task-231). **Mesure au smoke test contre vrai serveur** : deux envois d'une session passent
de `CONNECT=1, AUTH=1, SEND=2, NOOP=1` à **`NOOP=0`**.

### Remède 3 — correction du diagnostic de la US (cinquième de la semaine)

La US affirme « aucune mise en cache des réponses de révocation ». **C'est faux** : le cache
OCSP existe depuis **task-069** (Redis, fraîcheur 1 h configurable, fenêtre de grâce
Option C, RÉVOQUÉ honoré quel que soit l'âge) et le cache CRL aussi (borné par `NextUpdate`).
Les tests demandés par le DOD existent déjà (`CertificateValidatorTests`). **Rien à
construire** — le poste OCSP était déjà amorti ; ce sont les reconnexions elles-mêmes que les
remèdes 1 et 2 suppriment. Les items OCSP du DOD sont donc satisfaits **par l'existant**,
constaté et non réécrit.

### Défaut préexistant réparé

`MailClientSession.Dispose` n'était **pas idempotent** (second `Dispose` →
`ObjectDisposedException` sur le CTS) — exposé par les nouveaux tests, garde posée. Le
nettoyage de session et un logout concurrent pouvaient se marcher dessus.

### Tests

5 nouveaux (keep-alive) + 2 nouveaux (sonde) + 2 adaptés au nouveau contrat — dont le smoke
`NOOP=0`, qui est la mesure du remède 2 sur vraie socket. **Preuve par mutation** : condition
d'âge inversée → le test de réutilisation fraîche échoue. Les tests de sonde font répondre
« morte » au substitut **exprès** : si la sonde était consultée sur le chemin frais, le test
le verrait par la reconnexion.

### Validation

Build 0 erreur / 0 avertissement · domain 136/136 · infrastructure 419/419 ·
application **2037/2037** · api 650/650 · integration **369/369** (16 ignorés).

### 🚧 Contre-épreuve au banc — bloquante pour le merge, non faite ici

Le DOD l'exige : tir `journey` n200 K=1 iso-conditions — `send` p50 ≤ 1 000 ms (réf. 1 229),
part du temps serveur en baisse (réf. 17,9 %), `IOException` de sonde en forte baisse
(réf. 1 345), ~1 connexion par session au rythme réel. Le banc n'est pas monté dans ce cycle.


## Simplify log

**Skip propre.** Le diff (401 lignes, 9 fichiers) est déjà factorisé : signal de santé et
démarrage idempotent centralisés dans la session, décision d'âge en un seul point du factory.
Candidat non retenu : deux helpers d'attente-par-scrutation privés quasi identiques dans deux
classes de test (`EventuallyAsync` / `WaitUntilAsync`) — utilitaire sans risque de dérive
sémantique, à mutualiser opportunément lors d'un prochain passage dans ces fichiers.


## Sonar log

Scan direct sur la branche `fix/task-238-smtp-keepalive-sonde-ocsp` (scanner local, EXECUTION SUCCESS).

### KPIs qualité (baseline → final)

| Métrique | Baseline (task-237) | Final (task-238) |
|---|---|---|
| Quality Gate (new code) | **ERROR** | **ERROR** |
| `new_violations` | 35 | **28** |
| `new_bugs` | 0 | 1 (`report.py` S1244 — task-174, hérité) |
| `new_coverage` | 0.0 % (aucun rapport importé) | **86.9 % — OK** ✅ |
| `new_security_hotspots_reviewed` | 0.0 % | 71.4 % (2 restants) |
| `new_duplicated_lines_density` | — | 0.08 % — OK |

### Attribution

- **Zéro** des 28 violations dans un fichier touché par task-238 (`MailClientSession`,
  `SmtpConnectionFactory`, `SmtpSessionSlot`, `MailSessionTimeouts`, `MailServersOptions`,
  `MailServerDiscovery`, tests) — la passe n'a rien à corriger sur le code de la task.
- 24/28 dans l'outillage de banc `tests/loadtest-k6/` (tasks 174/195) : `report.py` (15,
  dont le new bug S1244 et 8 S3776), `journey.js` + `journey-model.js` (9). Les 2 hotspots
  non révisés = `Math.random()` de `journey.js` — **9ᵉ signalement**.
- 2 S103 hérités hors task : `BaseRepository.cs`, `IIheXdmProcessingService.cs`.

### Fait notable

**Le mur `new_coverage = 0` est tombé** : un rapport de couverture est désormais importé et
la condition passe (86.9 % ≥ 80). Les deux causes restantes du QG ERROR sont entièrement
héritées (hotspots jamais révisés + violations d'outillage k6).

**Décision** : acceptation best-effort, aucune itération de fix — rien à corriger dans le
périmètre de la task, et les findings restants appartiennent aux tasks d'outillage.


## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/168 — label `awaiting-human-merge`. ⚠️ Aucun check CI remonté à l'ouverture (Actions s'est rétabli le matin même après la panne du 2026-08-06 — le run develop post-merge de task-237 est passé VERT, règle 5 soldée) ; vérifier que le run PR apparaît avant le merge.
- `dtos-mss` : branche auto-incluse **vide** (0 commit), aucune PR — **7ᵉ occurrence** du défaut de cycle « branche auto-incluse jamais utilisée ».

## Code Review Summary

**APPROVED — 0 blocage** (9 fichiers revus, diff 401 lignes).

- Flux de contrôle de l'emprunt sûr : early-return fenêtre-fraîche dans le `try`, `catch` libère le jeton (`slot.Dispose()`), jamais de slot orphelin.
- Pas de course NOOP/DATA : battement en `Wait(0)` (n'attend jamais), écartement sur échec effectué verrou détenu, `finally` libère.
- Signal de santé distinct de `LastSmtpAccessTime` — justifié dans le code (l'accès est rafraîchi avant qu'on sache si la connexion vit).
- Aucune donnée de santé dans les logs (SessionId technique uniquement).
- ⚠️ Trade-off documenté (non bloquant) : fenêtre sans-sonde ≤ 60 s → une connexion tuée à l'instant peut servir un envoi qui échouera ; probabilité bornée par le keep-alive 30 s qui écarte les morts. Inhérent à toute sonde conditionnée à l'âge.
- Au passage : `Dispose` rendu idempotent (garde `_disposed`) — défaut pré-existant exposé par un test du keep-alive.

**Validation finale /review** : build 0 erreur ; suites 136 / 419 / 2037 / 650 / 369 (16 ignorés) — tout vert sur bin normal.
**DOD** : tous les items vérifiés ; item « cache OCSP/CRL » couvert par les tests de task-069 (correction de diagnostic — le cache existe depuis task-069, rien à construire) ; item « contre-épreuve au banc » = **bloquant pour le MERGE, non fait** (banc non monté) — consigné dans la PR.
