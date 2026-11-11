# todo-task-458.md — Notes internes sur un message

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: done-task-457 (personnes de la boîte, attribution)
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. Travail à plusieurs dans la boîte partagée. Aujourd'hui,
la secrétaire et le médecin se parlent à côté du message (post-it, téléphone, mail ordinaire).

> **Origine.** Analyse du 2026-11-11, manque C3 (Front, Spark, Missive, HEY : commentaires internes jamais envoyés à
> l'expéditeur).

## Ce qui est établi

- La seule note existante est celle de l'acquittement de biologie : 500 caractères, par document, biologie seulement.
- Le panneau « Actions & dossier » de weda2 (`MailSidePanelComponent`, sections `ack | duplicate | patient |
  attachments | tags`, injectées par `[mssPanelSection]`) est le point d'extension prévu.
- Le mobile n'a pas de panneau : l'acquittement est dans `mail-body.component.html`.

## Objective

Toute personne de la boîte écrit une **note interne** sur un message : « Patient rappelé, RDV jeudi », « Dr, à valider
avant envoi au patient ». La note n'est **jamais envoyée** à l'expéditeur ni à personne hors de la boîte. Elle est
imputée et visible de toute l'équipe de la boîte.

Règles :
- **Contenu** : texte libre de 1 000 caractères au plus. Pas de pièce jointe.
- **Ajout seul** : une note ne se modifie ni ne se supprime. On corrige par une nouvelle note. L'historique est
  chronologique.
- **Chaque note** affiche son auteur, son rôle, la date et l'heure (« Cyril DELEGUE (délégataire), 12/11 10:14 »).
- **Jamais envoyée** :
  - absente de la réponse, du transfert, de l'impression, de l'export EML ;
  - absente de « Importer dans Weda » ;
  - absente de la synthèse et du chat IA.
- **Signalée sur la ligne** : une pastille « note » avec le nombre de notes.
- **Avertir** : une note sur un message attribué (task-457) avertit la personne attribuée, si ce n'est pas elle qui
  écrit. La notification ne cite pas le texte.
- **Où** : nouvelle section « Notes » du panneau « Actions & dossier » sur weda2 ; section « Notes de l'équipe » du
  détail sur mobile.
- **Ancrage** selon task-453.

### Hors périmètre

- Mentionner une personne (« @Cyril ») dans une note.
- Notes rattachées au patient plutôt qu'au message.

## Definition of Done

- [ ] Notes stockées dans la base de la boîte, ancrées selon l'ADR de task-453 ; migration FluentMigrator, audit
      (règle 7c).
- [ ] Contrat : notes du message et leur nombre dans `MailDto` ; ajout de note ; paquet DTO publié.
- [ ] Acte d'audit `MailInternalNoteAdded` (le texte de la note n'entre **jamais** dans la trace) ; miroirs
      TypeScript ; `HealthDataAccess`.
- [ ] Tests unitaires : limite de 1 000 caractères, ordre chronologique, aucune modification ni suppression possible,
      note absente de la réponse, du transfert, de l'impression, de l'export et du contexte IA.
- [ ] **Test d'intégration de bout en bout (règle 1b), deux personnes sur la même boîte**, sur
      `POST api/v1/Mail/emails/{id}/notes` :
      - le délégataire ajoute une note, le titulaire la relit avec l'auteur réel ;
      - une réponse envoyée ensuite (GreenMail) ne contient pas le texte de la note ;
      - cas d'échec : 1 001 caractères → 400 en `ProblemDetails`.
      Vu rouge.
- [ ] Test d'intégration : une personne d'une autre boîte ne lit pas les notes (403).
- [ ] Tests de composant (weda2 et mobile), vus rouges par mutation : ajout, affichage de l'auteur, pastille sur la
      ligne, limite de taille.
- [ ] **Scénario e2e** `E2E-NOTE-001` v1, mobile et angular requis, vu rouge : la secrétaire ajoute une note, le
      médecin la voit avec son nom, et la réponse envoyée ne la contient pas.
- [ ] Aucune note dans les logs ; `data-testid` ; conventions de libellés.
- [ ] Build et tests verts (api-mail, Dtos, weda2, mobile) ; client-angular : code-only.

## Manual Test Plan

1. Boîte du médecin avec une secrétaire délégataire : secrétaire sur le mobile, médecin sur weda2.
2. Secrétaire : sur un courrier, « Notes de l'équipe » → « Patient rappelé, RDV jeudi 9 h ».
3. Médecin : la ligne porte la pastille « 1 note » ; le panneau « Notes » montre le texte, avec « Cyril DELEGUE
   (délégataire) » et l'heure.
4. Médecin : répondre au message, puis ouvrir la réponse dans Envoyés : la note n'y figure pas. Imprimer : la note
   n'y figure pas.
5. Attribuer le message au médecin (task-457), puis ajouter une note côté secrétaire : le médecin est averti.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — la note est libre ; aucune donnée d'identité n'est extraite ni affichée par le système
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel
- **Habilitations** : personnes rattachées à la boîte sous verdict récent de l'opérateur (règle 14)
- **Interop CI-SIS** : non applicable — la note n'est jamais transmise
- **Tracé PGSSI-S** : `MailInternalNoteAdded` au nom de l'auteur (sans le texte) ; `HealthDataAccess`, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — la note peut contenir des données de santé ; stockée dans la base de la boîte (HDS)
- **AIPD / impact RGPD** : à mettre à jour — nouveau contenu libre susceptible de porter des données de santé, durée de
  conservation alignée sur celle du message
