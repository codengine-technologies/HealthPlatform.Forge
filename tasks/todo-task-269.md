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
