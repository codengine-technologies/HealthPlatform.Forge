# todo-task-269.md — L'envoi ne paie plus une session SMTP fraîche à chaque message

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015

## Objectif

L'envoi est la **seule étape rouge** de la grille SLO de la campagne du
2026-08-23 (`Api/Mail/tests/loadtest-k6/reports/2026-08-23/report-journey-500-esc-20260823-220658.md`),
et elle ne l'est plus qu'au **p50** : 1 144 ms pour une cible de 1 000 (le p95,
1 741 ms, passe largement sous 3 000). C'est aussi le **premier poste du temps
serveur** (24,0 %, 6 392,9 s au palier 500).

La décomposition task-260 — première campagne où elle tourne — donne la cause
en trois tiers quasi égaux, et le premier est celui-ci :

| Phase | Moyenne | p95 | Lecture |
|---|---|---|---|
| `acquire_session` | **412 ms** | 491 | ~4 allers-retours (TCP + TLS + AUTH) : **une session SMTP fraîche à chaque envoi ou presque** — le p95 serré dit que ce n'est pas une queue, c'est un coût payé systématiquement |
| `smtp_transmit` | 376 ms | 488 | MAIL/RCPT/DATA/acquittement |
| `archive_sent` | 379 ms | 823 | append IMAP vers Sent (partage la session praticien depuis task-216 — attendu) |
| `build_mime` | 19,5 ms | 43 | négligeable |

À ~100 ms de latence MSSanté par aller-retour, l'envoi paie **~11-12
allers-retours réseau en série**. La session IMAP du praticien est poolée et
réutilisée (task-036 et suivantes) ; la session SMTP ne l'est pas.

S'y ajoute un second fait mesuré, peut-être le même défaut : **~1,9
`SmtpCommandException` par envoi** (25 038 pour ~13 300 envois — Prometheus
`dotnet_exceptions_total`, fenêtre du tir). C'était ≈3,1 le 2026-08-14. Des
commandes SMTP sont rejouées à chaque envoi : des allers-retours payés deux
fois. **Établir cette cause fait partie de la US** — si le rejeu vient d'une
session périmée réutilisée naïvement, le pool devra gérer la péremption
(NOOP de sonde, ré-établissement), pas la masquer.

**Contenu attendu** (technique à arbitrer par `/develop`, l'intention est
métier) : le deuxième envoi d'un praticien dans la même session applicative ne
repaie ni TCP, ni TLS, ni AUTH — par réutilisation/pool de la connexion SMTP
par praticien, symétrique du pool IMAP existant. Une session SMTP MailKit
n'est pas thread-safe : la sérialisation par praticien suit le modèle du
verrou `smtp_session` existant.

**Gain attendu** : ~400 ms par envoi sur le p50 → sous la cible de 1 000 ms
(1 144 − ~400 ≈ 750). L'élimination des rejeux de commandes peut en apporter
davantage sur `smtp_transmit`.

**Ce qui n'est PAS dans le périmètre** : l'archivage Sent (`archive_sent`,
tranché par task-216 — il partage la session IMAP du praticien, ne pas y
retoucher) ; le regroupement des allers-retours IMAP d'enrichissement.

## Definition of Done

- [ ] Build passes (0 errors), tests pass (0 failures) sur api-mail
- [ ] La cause des ~1,9 `SmtpCommandException`/envoi est **établie et écrite**
      (dans la task au fil de l'implémentation) avant le choix du remède —
      un correctif écrit sur une cause supposée est le mode d'échec payé par
      task-222
- [ ] Deux envois successifs du même praticien ne paient qu'un seul
      établissement de session SMTP (test d'intégration : le second envoi ne
      déclenche ni connexion ni AUTH — vérifiable par le compteur de
      sollicitations `connect`/`authenticate` de task-225/262)
- [ ] Une session SMTP périmée/déconnectée est détectée et ré-établie sans
      échec visible du médecin (test : session fermée côté serveur entre deux
      envois → second envoi réussit)
- [ ] Le verrou de session SMTP interdit deux envois concurrents sur la même
      connexion (une session MailKit n'est pas thread-safe) — test unitaire
- [ ] `SendOperationScope` (task-260) continue de décomposer : `acquire_session`
      proche de zéro sur session réutilisée, coût plein sur session fraîche —
      >= 1 test par branche
- [ ] Unit tests pour tout nouveau service/handler (>= 1 par méthode publique)
- [ ] Aucune donnée de santé en clair dans les logs (contenu MSSanté, INS)
- [ ] Le log Warning `🔐 SMTP auth … TokenPreview=` (un par envoi, aperçu de
      token en clair) passe en Debug ou disparaît — constaté au tir du
      2026-08-23, hygiène de journalisation PGSSI-S

## Manual Test Plan

- Lancer le banc local : `cd Api/Mail && dotnet run --project src/AppHost --launch-profile https-load-test`
- Seeder : `dotnet run --project tests/mss.mail.loadtest.seed -- --users 5 --messages 10 --api http://127.0.0.1:5052`
- Envoyer deux messages successifs avec la même identité virtuelle
  (`POST /api/v1/mail/sendmail`, en-têtes loadtest-1, `Client-Session-Id` stable)
- Vérifier dans Seq : un seul `SmtpConnect` pour les deux envois ; aucun
  `SmtpCommandException` ; le second envoi sensiblement plus rapide
- **Au banc (clôture de l'US, non bloquant pour le merge)** : tir journey
  distant iso-conditions avec la campagne du 2026-08-23 (corpus fileté 0,3,
  UID_BASE selon l'état du maildir) — `send` p50 < 1 000 ms au palier 500,
  `SmtpCommandException`/envoi ≈ 0

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — optimisation de performance interne, aucun changement fonctionnel
- **Exigences DSR honorées** : non applicable — comportement fonctionnel inchangé
- **INS** : non applicable — aucun traitement patient modifié
- **Authentification PS** : inchangée (PSC en amont ; l'AUTH SMTP réutilise le token existant — la réutilisation de session ne doit pas prolonger une session au-delà de la validité du token : point à vérifier à l'implémentation)
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — le MIME émis est inchangé
- **Tracé PGSSI-S** : l'évènement d'envoi MSSanté reste journalisé à l'identique ; retrait de l'aperçu de token des logs (garde-fou « aucun secret en clair »)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — inchangé
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement de données

## Branches
- `api-mail` (pushed) : feat/task-269-smtp-session-pool — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-269-smtp-session-pool
- `dtos-mss` (pushed, auto-inclus) : feat/task-269-smtp-session-pool — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-269-smtp-session-pool

## Journal d'implémentation (/develop, 2026-08-25)

### Cause établie AVANT le remède (exigence DOD) — sur pièces

**Le pool SMTP existait déjà et était correct** (task-231 : `SmtpSessionSlot`,
pas de QUIT après envoi ; task-238 : sonde-par-âge + keep-alive ; task-241 :
battement compté). Le défaut n'était pas l'absence de pool mais **une course
perdue de son entretien** :

1. **Le serveur du banc coupe toute connexion SMTP inactive entre 28 et 35 s**
   (mesuré à la prise, GreenMail direct ET via Toxiproxy — Toxiproxy hors de
   cause ; un NOOP toutes les 15 s la tient indéfiniment).
2. **Le battement SMTP vivait sur la cadence IMAP : 30 s** — pile sur le seuil.
   Course perdue en un ou deux cycles. Preuve compteur : **1 seul NOOP
   `SmtpKeepAlive`** sur une session de plusieurs minutes (Prometheus local).
3. **Le battement perdant avale l'exception en LogDebug et jette le client**
   (`SendSmtpKeepAliveNoopAsync`) : au prochain emprunt `slot.Client == null`,
   la sonde n'est jamais atteinte — reproduction locale : 84 envois → 84
   connexions fraîches, 0 sonde « morte », 0 éviction, zéro trace.
4. **Second étage au rythme réel multi-réplicas** : même keep-alive réparé,
   l'éviction `SmtpIdleTimeout=5 min` refermait la connexion entre deux envois
   d'un même réplica (~17 min d'écart à 5 réplicas au palier 1000).

**Les ~1,9 `SmtpCommandException`/envoi** : comptées par Prometheus
(`dotnet_exceptions_total`), **zéro occurrence dans Seq** sur tout le tir du
2026-08-24 — ce sont des exceptions levées puis avalées, cohérentes avec les
battements de keep-alive mourant en silence (un par mort de connexion ×
sessions × durée) et les QUIT sur connexions déjà coupées. Le dénominateur
« par envoi » était une coïncidence de ratio, pas un rejeu de commandes
d'envoi : aucun rejeu sur le chemin `SendAsync` n'a été observé. Le remède
n'est donc PAS un rejeu géré, mais la fin des morts silencieuses (cadence) et
leur visibilité (log Information par mort réelle).

### Remède (3 pièces, api-mail seul, contrat d'API inchangé)

- **Cadence SMTP dédiée** : `MailSessionTimeouts.SmtpKeepAliveInterval`
  (défaut 15 s — sous le seuil mesuré de ~30 s ; 0 = hériter de la cadence
  IMAP), configurable par domaine (`MailServers:*:SmtpKeepAliveInterval`).
  Boucle de session à deux échéances indépendantes.
- **Rétention découplée** : `SmtpConnectionRetention` (défaut : la connexion
  vit avec la session ; 0 = retomber sur `SmtpIdleTimeout`), configurable par
  domaine. `SmtpIdleTimeout` garde son rôle dans l'expiration de session —
  allonger la rétention ne prolonge JAMAIS la vie de la session ni ses sièges
  IMAP. Un opérateur exigeant la restitution anticipée du siège SMTP la
  configure par domaine.
- **Mort visible** : l'échec du NOOP d'entretien passe de LogDebug à
  LogInformation (type d'exception nommé) ; le log `🔐 SMTP auth …
  TokenPreview=` (Warning, aperçu de token en clair) devient un Debug **sans
  aperçu** (PGSSI-S).

### Validation

- Build 0 erreur ; **3 884 tests, 0 échec** (dont 2 nouveaux : cadence SMTP
  dédiée, rétention par défaut ; 2 adaptés : éviction sur rétention
  configurée ; réutilisation/sonde/verrou task-231/238 inchangés et verts).
- Reproduction locale pré-correctif : envois 2 s d'écart réutilisés (~0,75 s)
  mais +75 s TOUJOURS frais — post-correctif attendu : réutilisation à tout
  écart tant que la session vit (contre-épreuve au banc à la clôture).

### Hors périmètre constaté en route

- `MdnService` ouvre une connexion SMTP **fraîche par accusé de lecture**
  (`CreateConnectedClientAsync` direct, sans pool) — invisible au banc (pas de
  demandes d'accusé dans le corpus). À instruire si les MDN prennent du volume.

## Simplify log (/forge-simplify, 2026-08-25)

- **Efficacité** : `IdentifyTokenSource` (décodage JWT) évalué à chaque
  connexion fraîche même Debug coupé (les arguments d'un `LogDebug` sont
  toujours évalués) → garde `logger.IsEnabled(LogLevel.Debug)`. Commit
  `refactor(smtp)` poussé, build + 2 166 tests application verts.
- **Examinés sans action** : boucle keep-alive à deux échéances (duplication
  apparente mais gardes par voie différents — extraire masquerait plus que ça
  ne factorise) ; `tick` recalculé par itération (propriétés mutables par les
  tests, coût nul).
- `dtos-mss`/`interop-cda` non touchés (porteurs de contrat — hors périmètre).

## Sonar log (/sonar, 2026-08-25 — mode chaîné, 2 itérations)

| KPI | Baseline (post-develop) | Final | Cible |
|---|---|---|---|
| Quality Gate | OK | **OK** | OK |
| Bugs / Vulnérabilités | 0 / 0 | **0 / 0** | 0 / 0 |
| Violations new-code | 37 | **35** | best-effort |
| Couverture new-code | 91,1 % | 91,0 % | ≥ 91 (gate) |
| Couverture globale | 88,0 % | 88,0 % | — |
| Code smells (projet) | 64 | 62 | — |

- **Corrigé (it. 2)** : S3776 sur la boucle keep-alive (complexité 22 → décomposée
  `KeepAliveLoopAsync` + `BeatImapLaneIfDueAsync`/`BeatSmtpLaneIfDueAsync` — code
  frais de la task, hors du champ du /sonar-s3776 manuel qui ne vise que le
  legacy) ; CA1816 sur `SmtpSessionKeepAliveTests.Dispose`.
- **Acceptés (faux positifs, non corrigés à dessein)** : S3604 ×9 (« member
  initializer redundant » sur classes à constructeur primaire C# 12 — retirer les
  initialiseurs casserait l'initialisation, FP connu du scanner) ; S125 ×3
  (« commented out code » sur des commentaires en prose contenant des fragments
  code-like).
- **Hors périmètre task-269** : S107/S3267/S4456/S4457/CA1859/CA1861/xUnit2032
  dans des fichiers du lot précédent (new-code period plus large que le diff de
  la task) — laissés aux cycles qui les portent.
- Note SonarQube : conteneurs `sonarqube`/`sonarqube_db` trouvés arrêtés
  (reboot) et relancés ; piège MSYS sur les arguments `/k:`/`/d:` du scanner
  (poser `MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'` avant `sonarscanner`).

## Lint log (/lint-angular, 2026-08-25)

- Skip propre : `client-angular` non listé dans **Repos** et non touché par la task.

## Lint mobile log (/lint-mobile, 2026-08-25)

- Skip propre : `client-mobile` non listé dans **Repos** et non touché par la task.

## Visual verify log (/verify-visual, 2026-08-25)

- Skip propre : aucun écran `client-mobile` touché (task backend uniquement).

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/201 — label `awaiting-human-merge`
- `dtos-mss` : aucun commit (pas de changement de contrat) — pas de PR ; branche `feat/task-269-smtp-session-pool` à supprimer au /merge
- `client-blazor` / `client-angular` / `client-mobile` : non concernés (US backend seule, justifiée dans le corps)

## Code Review Summary

APPROVED — 9 fichiers, 0 bloquant, 1 suggestion (cadence de relance du NOOP IMAP en échec répété avec IsConnected=true — cas rare, à lisser si observé), 1 flaky pré-existant identifié hors diff (EnrichmentOperationScopeTests, pollution Meter sous parallélisme — candidat US harnais).
