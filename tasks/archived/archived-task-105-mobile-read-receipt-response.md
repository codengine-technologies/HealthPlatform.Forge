# todo-task-105-mobile-read-receipt-response.md — Accusé de lecture : envoi en réponse à une demande

**Repos**: client-mobile
**Single frontend**: true
**Dependencies**: none
**Epic**: E012

> **US mono-repo justifiée** : l'endpoint backend existe déjà
> (`POST …/emails/{uid}/sendreadreceipt`) ; l'écart est uniquement côté
> `client-mobile` qui *demande* un accusé (compose) mais ne *répond pas* à une
> demande reçue. Parité avec `client-angular`.

## Objective

Quand le médecin ouvre un email **reçu** dont l'expéditeur a **demandé un accusé
de lecture** (Disposition-Notification, `mail.requestReadReceipt === true`), le
client mobile doit pouvoir **émettre l'accusé** via l'API, avec consentement
explicite du PS (l'accusé de lecture MSSanté n'est jamais émis à l'insu de
l'utilisateur).

## Analyse de référence

- API : `sendReadReceipt(folderPath, uid)` → `POST /api/v1/mail/folders/{folder}/emails/{uid}/sendreadreceipt`.
- Détection : sur le `MailDto` reçu, `requestReadReceipt === true` ET le mail
  n'est pas un message envoyé (folder ≠ Sent) ni un brouillon.

## Comportement attendu

- À l'ouverture d'un email reçu demandant un accusé : afficher un bandeau
  « L'expéditeur a demandé un accusé de lecture » + bouton « Envoyer l'accusé ».
- Sur action du PS : appel `sendReadReceipt` ; confirmation (toast) au succès.
- Une fois envoyé (dans la session), ne plus reproposer pour ce mail.
- Échec API : message clair (ProblemDetails), pas d'état incohérent.
- Aucun envoi automatique sans action utilisateur (consentement PS).

## Scénarios d'acceptation

1. **Demande présente** — Étant donné un email reçu avec demande d'accusé,
   quand je l'ouvre, alors un bandeau propose d'envoyer l'accusé.
2. **Envoi** — Quand je confirme l'envoi, alors l'accusé est émis et une
   confirmation s'affiche ; le bandeau disparaît.
3. **Pas de demande** — Pour un email sans demande d'accusé, aucun bandeau.
4. **Message envoyé** — Sur un mail du dossier « Envoyés », aucun bandeau.
5. **Échec** — Si l'API échoue, un message clair s'affiche, sans bloquer la consultation.

## Definition of Done

- [ ] Build passes (`npm run build`, 0 erreur)
- [ ] Tests pass (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 échec)
- [ ] `MssApiService.sendReadReceipt(folderPath, uid)` implémenté
- [ ] Bandeau + bouton d'envoi dans `mss-mail-detail`, conditionné à `requestReadReceipt` (mail reçu)
- [ ] Envoi sur action utilisateur uniquement (pas d'auto-envoi) ; idempotent dans la session
- [ ] Gestion d'erreur `ProblemDetails`
- [ ] Libellés FR en dur ; `data-testid` sur le bandeau et le bouton
- [ ] Tests : `mss-api.sendReadReceipt` (POST endpoint), `mss-mail-detail` (bandeau visible si demande / envoi déclenche l'appel / masqué après envoi)
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Backend `cd Api/Mail && dotnet run` ; Mobile `cd Client/Mobile && npm start`
- Se connecter (PSC), ouvrir un email **reçu** avec demande d'accusé de lecture
- Vérifier le bandeau ; envoyer l'accusé → confirmation ; le bandeau disparaît
- Ouvrir un email sans demande → pas de bandeau ; ouvrir un « Envoyé » → pas de bandeau
- Comparer le comportement avec `client-angular`

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : MSSanté — accusé de lecture (disposition notification)
- **Authentification PS** : PSC / e-CPS (en place) ; l'accusé est imputé au PS authentifié
- **MSSanté** : accusé émis depuis la boîte du PS ; jamais de RPPS dans l'objet/en-têtes
- **Tracé PGSSI-S** : émission d'un accusé de lecture journalisée côté backend — imputabilité, conservation 6 ans
- **Consentement** : l'accusé n'est émis que sur action explicite du PS (jamais automatique)
- **Sécurité** : aucune donnée de santé en clair dans les logs
- **AIPD / RGPD** : inchangé — fonction d'accusé de réception standard MSSanté

## Branches
- `client-mobile` (pushed) : feat/task-105-mobile-read-receipt-response — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-105-mobile-read-receipt-response

> Single frontend (client-mobile only). Deps none (socle E012 sur develop).

## Develop log
- Repos : client-mobile
- mss-api.sendReadReceipt ; mss-mail-detail bandeau accusé (reçu + requestReadReceipt, hors Envoyés/brouillon), envoi sur consentement, idempotent session
- Build ✓ · Tests ✓ 90/90 (3 nouveaux) · Lint ✓
- Commit : client-mobile @571a876

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/10 — label `awaiting-human-merge`

## Code Review Summary
- Verdict : APPROVED · Build ✓ · Tests ✓ 90/90 · Lint ✓
- Consentement explicite, idempotence, ProblemDetails ; pas de RPPS/données santé en clair ; FR + data-testid

## Merged
- Merged : 2026-06-19 (squash) by human authorization
- client-mobile : develop @1f41098 (PR #10 closed)
- Local feature branch conservée
