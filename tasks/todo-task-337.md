# todo-task-337.md — Le journal d'audit ne perd plus de traces saines à cause d'une seule trace invalide, ni pendant une panne de cache

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E016
**Single frontend**: true
**Priorité**: **2** — une seule trace invalide fait supprimer **tout son lot** de traces réglementaires ; une erreur de déploiement transitoire (droit ou partition manquante) efface le journal en cinq passes ; une panne Redis inonde le journal et désactive la garde de réutilisation de session.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-17**, **AUD-58**). Contraire à l'invariant
> task-292 : aucune trace ne se perd en silence.

## Ce qui est établi (develop @ `14d58398`)

1. **Lot poison (AUD-17)** — `AuditBackgroundService.cs:178-231, 280-304`, `PostgresAuditSink.cs:86-144` :
   l'insertion d'un lot est une transaction ; une trace invalide (`\0` dans un sujet, SqlState 22021)
   fait échouer toutes les autres ; `ParkFailedTraceAsync` incrémente `TransportAttempts` pour **toutes**
   et leur applique `IsPoison(ex)` (vrai pour toutes) ; rejouées ensemble, les traces saines épuisent
   leurs 5 tentatives et sont supprimées (« LOST »).
2. **Classes d'erreur** — `42501 insufficient_privilege` et `42P01 undefined_table` sont classées poison :
   un rôle ou une partition mal provisionnés au déploiement font perdre tout le journal en 5 passes rapides.
3. **Panne Redis (AUD-58)** — `SessionMailboxGuard.cs:153-158`, `UserContextEnricherMiddleware.cs:249-268`,
   `Sdk/Services/ResilientCacheService.cs:46-82` : `GetAsync` rend `default` et `SetAsync` avale l'erreur →
   chaque requête obtient `Bound` et écrit une trace `MailboxSessionOpened` ; le refus 409 de réutilisation
   d'identifiant de session n'est plus appliqué.

## Objective

Qu'**une trace d'audit valide ne soit jamais perdue** à cause d'une autre trace, d'une erreur de
provisionnement ou d'une panne de cache ; que seule la trace réellement invalide soit écartée, et que
cet écart soit visible.

### Périmètre

1. **Isolement du poison** : sur échec d'un lot classé poison, rejeu trace par trace (ou par bissection)
   pour isoler la fautive ; tentatives décomptées sur la seule trace isolée.
2. **Trace invalide** : si la cause est une donnée (caractère interdit), la trace est **assainie** puis
   écrite (le caractère retiré est signalé), plutôt que perdue — choix justifié par `/develop`.
3. **Classes d'erreur** : 42501 et 42P01 sortent de la classe poison (erreurs d'infrastructure →
   rétention en spill, alerte), jamais de suppression.
4. **Garde de session** : distinguer « clé absente » de « cache indisponible » (retour tri-état) ; en
   indisponibilité, pas de trace `MailboxSessionOpened` par requête, et comportement de la garde
   documenté (refus ou tolérance explicite — arbitrage à consigner).
5. **Métriques** : traces isolées comme poison, assainies et en spill comptées.

### Hors périmètre

- La rétention et la purge (`AuditRetentionHostedService`) — jugées saines par l'audit.
- La copie d'identité en tâche de fond (task-334).

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Tests rouges d'abord** (log des runs rouges dans le task file), rouges sur le code actuel :
  - [ ] lot de 10 traces dont une contient `\0` → sur le code actuel les 10 finissent « LOST » ; après correctif 9 écrites, 1 assainie ou isolée
  - [ ] erreur 42501 simulée sur un lot → aucune trace supprimée, toutes conservées en spill
- [ ] Test : erreur 42P01 simulée → même comportement que 42501
- [ ] Test : cache indisponible → aucune trace `MailboxSessionOpened` par requête ; comportement de la garde conforme à l'arbitrage consigné
- [ ] Test d'intégration (Postgres Testcontainers) : lot poison réel → traces saines présentes en base
- [ ] Métriques poison / assainie / spill testées
- [ ] Non-régression task-292 : tests existants du spill et du transport verts
- [ ] INS : conservée dans la trace d'audit en base (arbitrage task-186), **jamais** dans les logs

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` ; praticien de test connecté.
2. Recevoir un mail de test dont le sujet contient un caractère nul (fixture du banc) puis faire plusieurs actions (lecture, déplacement).
3. Écran d'audit du praticien → **Attendu** : toutes les actions apparaissent ; la trace du sujet invalide est présente (assainie) ou signalée. Avant : le lot entier disparaît.
4. Révoquer temporairement le droit `INSERT` du rôle d'écriture d'audit (base de test), faire quelques actions, rétablir → les traces apparaissent après rétablissement (spill). Avant : perdues.
5. Arrêter Redis pendant la navigation → pas d'inondation de traces « session ouverte » dans l'écran d'audit.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — conformité de la traçabilité
- **Exigences DSR honorées** : non applicable — PGSSI-S § journalisation (intégrité et exhaustivité des traces)
- **INS** : l'INS reste dans la trace d'audit en base (finalité réglementaire, arbitrage 2026-09-07), jamais dans Seq / Graylog / OTLP
- **Authentification PS** : inchangée
- **Habilitations** : inchangées — lecture du journal bornée au tenant (RLS)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : **au cœur** — aucune trace valide perdue ; traces isolées ou assainies signalées ; rétention inchangée
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — journal d'audit mutualisé (E016)
- **AIPD / impact RGPD** : inchangé
