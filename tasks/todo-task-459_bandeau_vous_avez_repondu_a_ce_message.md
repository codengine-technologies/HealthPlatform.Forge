# todo-task-459.md — Bandeau « Vous avez répondu à ce message le… »

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: aucune
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. Savoir, en ouvrant un message, qu'on y a déjà répondu
évite de répondre deux fois et de rouvrir Envoyés. En boîte partagée, c'est savoir qu'un collègue l'a fait.

> **Origine.** Demande explicite de l'humain du 2026-11-11 : « un bandeau qui s'affiche sur un mail dont la réponse a
> été faite : *Vous avez répondu à ce message le…* ».

## Ce qui est établi

- Les messages envoyés sont en base. Le dossier Envoyés est synchronisé, et l'archivage d'un envoi fait par la
  plateforme passe par `SentArchiveDispatcher` puis `ImapService.AppendToSentAsync`.
- `Mail.InReplyTo` et `Mail.References` sont stockés, avec l'index `IX_Mails_InReplyTo`.
- `MailRepository.GetThreadAsync` calcule déjà `HasReplies = Mails.Any(m => m.InReplyTo == messageId)`.
- `Mail.IsAnswered` (drapeau IMAP `\Answered`) existe. Il ne donne ni la date ni l'auteur, et les drapeaux ne sont
  relus que pour les nouveaux UID.
- L'envoi « pour le compte de la boîte » (E020 F006) pose l'en-tête `Sender` au nom du délégataire. La trace d'audit
  `MailReply` porte la personne réelle.
- Piège : un accusé de lecture ou un rapport de distribution entrant peut porter `In-Reply-To`. Il ne doit jamais
  compter comme une réponse.

## Objective

En ouvrant un message auquel la boîte a répondu, le lecteur voit un bandeau :
- **« Vous avez répondu à ce message le {date} à {heure} »**, si c'est lui ;
- **« {Prénom NOM} ({rôle}) a répondu à ce message le {date} à {heure} »**, si c'est une autre personne de la boîte ;
- **« Une réponse a été envoyée le {date} à {heure} »**, si la réponse est partie d'un autre logiciel et que l'auteur
  n'est pas connu.

Règles :
- **Lien « Voir la réponse »** : il ouvre le message envoyé.
- **Plusieurs réponses** : le bandeau montre la dernière et le nombre total (« … le 12/11 à 10 h 14 — 2 réponses »).
- **Ce qui compte comme réponse** : un message de la boîte, envoyé (dossier Envoyés), dont `In-Reply-To` ou
  `References` désigne ce message. Les accusés de lecture et les rapports de distribution sont exclus.
- **Dans la liste** : une icône « répondu » sur la ligne (weda2 et mobile), avec la même info au survol ou à l'appui
  long.
- **Drapeau IMAP** : une réponse envoyée par la plateforme pose `\Answered` sur le message d'origine, si ce n'est déjà
  fait. À vérifier, et à poser si c'est absent.
- **Transfert** : hors périmètre de cette task.

## Definition of Done

- [ ] Contrat : dernière réponse (date, auteur connu ou non, identifiant du message envoyé) et nombre de réponses dans
      `MailDto` ; paquet DTO publié.
- [ ] Auteur de la réponse établi par la trace `MailReply` (personne réelle) ou l'en-tête `Sender` ; jamais la boîte
      quand l'auteur réel est connu (règle 14).
- [ ] Tests unitaires : réponse par `In-Reply-To`, réponse par `References` seul, accusé de lecture exclu, rapport de
      distribution exclu, deux réponses, auteur inconnu.
- [ ] **Test d'intégration de bout en bout (règle 1b)** sur `GET api/v1/Mail/folders/{f}/emails/{ids}` :
      - après une réponse envoyée par la plateforme (GreenMail et Dovecot), le message d'origine expose la date, la
        personne et le nombre de réponses, et porte `\Answered` côté IMAP ;
      - cas d'échec : un accusé de lecture entrant portant `In-Reply-To` ne crée **pas** de réponse.
      Vu rouge.
- [ ] **Deux personnes sur la même boîte** : le délégataire répond ; le titulaire lit « {délégataire} (délégataire) a
      répondu ».
- [ ] Tests de composant (weda2 et mobile), vus rouges par mutation : les trois libellés, « Voir la réponse »,
      plusieurs réponses, icône dans la liste.
- [ ] **Scénario e2e** `E2E-DETAIL-006` v1, mobile et angular requis, vu rouge : répondre à un message, revenir sur le
      message d'origine, le bandeau « Vous avez répondu à ce message le … » est là, et « Voir la réponse » ouvre
      l'envoi.
- [ ] `data-testid`, conventions de libellés, aucune donnée de santé dans les libellés ni les logs.
- [ ] Build et tests verts (api-mail, Dtos, weda2, mobile) ; client-angular : code-only.

## Manual Test Plan

1. Backend, weda2 et mobile sur la boîte de formation.
2. weda2 : répondre à un courrier. Revenir sur le courrier : « Vous avez répondu à ce message le … à … », avec « Voir
   la réponse » qui ouvre l'envoi. La ligne de la liste porte l'icône « répondu ».
3. Mobile, délégataire de la même boîte : ouvrir ce courrier : « {nom du titulaire} (titulaire) a répondu … ».
4. Répondre au même message depuis le webmail de l'opérateur, puis synchroniser : « Une réponse a été envoyée le … —
   2 réponses ».
5. Ouvrir un message dont seul un accusé de lecture est revenu : aucun bandeau.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel
- **Habilitations** : personnes rattachées à la boîte sous verdict de l'opérateur (règle 14)
- **Interop CI-SIS** : non applicable — en-têtes RFC 5322 (`In-Reply-To`, `References`) et RFC 3501 (`\Answered`)
- **Tracé PGSSI-S** : inchangé — l'envoi est déjà tracé (`MailReply`) au nom de la personne réelle
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — base de la boîte
- **AIPD / impact RGPD** : inchangé — l'auteur d'une réponse est déjà visible dans le journal de la boîte (E020)
