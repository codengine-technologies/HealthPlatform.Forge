# todo-task-340.md — L'accusé de lecture fonctionne de bout en bout : demandé selon la norme, envoyé une seule fois, enregistré et tracé comme réussi

**Repos**: api-mail
**Dependencies**: task-334 (la détection de la demande d'accusé sur les mails synchronisés en fond)
**Epic**: E009
**Single frontend**: true
**Priorité**: **3** — l'accusé de lecture demandé par le praticien est ignoré par les clients courants ; à la réception, l'accusé renvoyé échoue, ou part à chaque ouverture, et le journal d'audit l'enregistre en échec.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-32**, **AUD-43**).

## Ce qui est établi (develop @ `14d58398`)

1. **Envoi non persisté (AUD-32)** — `MailRepository.cs:2541-2555` (`MarkReadReceiptSentAsync`),
   `MailDataContext.cs:104-136` (aucun `HasColumnType` sur `ReadReceiptSentAt`), `MdnService.cs:58-95` :
   la valeur écrite par `NormalizeUtc` est de `Kind = Unspecified` ; EF mappe la propriété en
   `timestamptz` et Npgsql refuse cette valeur — le mécanisme que le contexte documente lui-même pour
   `SuppressionRequestedAt` (`MailDataContext.cs:217-224`). Conséquences : `ReadReceiptSentAt` jamais
   persisté → l'interface repropose l'accusé et en renvoie un à chaque ouverture ; audit
   `ReadReceiptSend Success=false` pour un accusé réellement envoyé ; erreur rendue au client. Un test
   (`MailRepositoryStatusCoverageTests.cs:148-153`) constate l'échec et l'attribue à tort à `EnsureCreated`.
2. **Demande non standard (AUD-43 a)** — `SmtpService.cs:355-358` n'émet que `Return-Receipt-To`
   (obsolète, ignoré par Outlook / Thunderbird) au lieu de `Disposition-Notification-To` (RFC 8098).
3. **Adresse inexploitable (AUD-43 b)** — `EmailAddressHelper.cs:51-62`, `MdnService.cs:111` : la valeur
   brute `"Dr X" <x@y.fr>` est passée comme **adresse** à `new MailboxAddress(string.Empty, …)` → échec
   d'analyse ou `RCPT TO` invalide ; seul le cas d'une adresse nue fonctionne.
4. **Format** — le MDN envoyé est un mail texte/HTML simple, pas un `multipart/report; report-type=disposition-notification`.

## Objective

Qu'une demande d'accusé soit **comprise par les clients de messagerie courants**, qu'un accusé reçu soit
renvoyé **une seule fois** à l'adresse correcte au format normalisé, et que son envoi soit enregistré et
tracé comme réussi.

### Périmètre

1. `ReadReceiptSentAt` mappé comme `timestamp without time zone` (convention du contexte), avec
   vérification de l'absence d'écart de modèle.
2. Émission de `Disposition-Notification-To` à la demande (conserver `Return-Receipt-To` en complément si
   `/develop` établit un besoin de compatibilité, justifié).
3. Analyse de l'en-tête reçu par `InternetAddressList.Parse`, première `MailboxAddress` retenue ; valeur
   invalide → pas d'envoi, événement journalisé.
4. MDN au format RFC 8098 (`multipart/report`, partie `message/disposition-notification`).
5. Correction de la note erronée du test de couverture.

### Hors périmètre

- La détection de la demande sur les mails synchronisés en fond (task-334, prérequis).
- L'interface de proposition d'accusé (inchangée).

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln` ; Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Test rouge d'abord** (intégration Postgres, log du run rouge dans le task file) : `MarkReadReceiptSentAsync` → sur le code actuel exception ; après correctif valeur persistée et relue
- [ ] Migration éventuelle auditée (règle 7c) : aucune opération fantôme, companion présent, « has pending changes » vide
- [ ] Test : message émis avec demande d'accusé → porte `Disposition-Notification-To`
- [ ] Test : en-tête reçu `"Dr X" <x@y.fr>` → accusé adressé à `x@y.fr` ; en-tête invalide → pas d'envoi, pas d'exception
- [ ] Test : MDN émis = `multipart/report; report-type=disposition-notification` avec la partie de notification
- [ ] Test : deuxième ouverture d'un mail dont l'accusé est parti → aucun second envoi
- [ ] Test : trace d'audit `ReadReceiptSend` en succès après un envoi réussi
- [ ] Test d'intégration endpoint (règle 1b) : envoi d'accusé de bout en bout (GreenMail) — accusé relu dans le puits
- [ ] Aucune adresse ni contenu en clair ajouté dans les logs

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` (profil banc, GreenMail) ; mobile ou Blazor.
2. Envoyer un message avec « demander un accusé de lecture » vers une boîte de test lue dans Thunderbird → Thunderbird propose l'accusé. Avant : aucune proposition.
3. Recevoir dans l'application un mail de test demandant un accusé avec un nom d'affichage (`"Dr Test" <test@…>`), l'ouvrir, accepter → l'accusé arrive chez l'expéditeur, au format accusé (reconnu comme tel par Thunderbird).
4. Rouvrir le même mail → aucune nouvelle proposition, aucun second accusé. Avant : à chaque ouverture.
5. Écran d'audit → l'envoi d'accusé apparaît en succès.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : accusé de lecture MSSanté (fonctionnalité existante rendue conforme à la RFC 8098)
- **INS** : non applicable
- **Authentification PS** : PSC / e-CPS inchangée pour l'envoi
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — norme de messagerie (RFC 8098)
- **Tracé PGSSI-S** : `ReadReceiptSend` tracé avec son vrai résultat
- **Consentement patient** : non applicable
- **Référentiels métier** : RFC 8098 (Message Disposition Notification)
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : inchangé
