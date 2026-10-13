# todo-task-376.md — Rédiger dans weda2 : jamais de contenu perdu, jamais de double envoi, jamais d'envoi incomplet présenté comme réussi

**Repos**: client-angular, api-mail
**Dependencies**: — (aucune)
**Epic**: E009
**Single frontend**: true — voir l'arbitrage sur le mobile ci-dessous.
**Priorité**: **1** — un courrier médical peut partir deux fois, partir sans ses pièces jointes avec « envoyé avec succès », annuler à tort un envoi antérieur, ou être perdu sans avertissement à la fermeture de la rédaction.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-14 ✔, ANG-15 ✔, ANG-16 ✔, ANG-17, ANG-18 ✔ (lecture et transfert), ANG-19, ANG-26, ANG-42, ANG-43, ANG-44, ANG-45, ANG-46, ANG-75**).

## Ce qui est établi

- **ANG-14** — la remise incertaine du serveur (503 `MAIL_DELIVERY_UNCERTAIN`, 502 de la route brouillon, décision task-330) n'est reconnue nulle part : la rédaction affiche « Erreur lors de l'envoi » et réactive Envoyer ; les envois en attente affichent « le message reste prêt à partir » ; le modèle n'a pas `deliveryUncertain`.
- **ANG-15** — `mail-compose.component.ts:707` : seul `doClose` vide le contexte « annule et remplace ». « Annuler et remplacer » sur X puis « Nouveau message » : le nouveau message part par `cancel-and-replace` et X est marqué « [ANNULÉ] ».
- **ANG-16** — `mail-compose.component.ts:509-541, 2125-2195` : l'identifiant de brouillon est posé avant toute création côté serveur ; `saveAndClose` fait un PUT (404 sur un id inconnu) et ferme : **tout le contenu est perdu**. Un premier autosave en échec rend l'envoi impossible.
- **ANG-17** — « Nouveau message », clic sur un brouillon de la liste, intention de l'hôte, rechargement : la rédaction est remplacée sans être enregistrée ; aucun `beforeunload`.
- **ANG-18** — `occurrence` jamais transmis : au transfert, deux pièces homonymes deviennent deux copies de la première ; à la lecture, la seconde n'est pas consultable.
- **ANG-19** — Envoyer est actif avant la fin du téléchargement des pièces d'un transfert : le message part sans elles.
- **ANG-26** — `failedActionsCount` ignoré ; une confirmation d'envoi est annulée en quittant la page.
- **ANG-42 à ANG-46, ANG-75** — un modèle écrase citation et signature ; signature en double ou sous la citation ; adresse saisie sans Entrée ignorée, Cc/Cci masqués mais destinataires ; refus explicites du serveur (taille, opposition, verrou) jamais affichés ; brouillon « annule et remplace » envoyé sans carte comme un message ordinaire ; autosave non relancé après échec, contact sans adresse principale, doublons de modèles, aperçu de correction d'un autre message, dialogue de doublons qui garde son acquittement.

## Objective

Que ce que le médecin écrit **ne soit jamais perdu**, qu'un message **ne parte jamais deux fois ni incomplet** sans qu'il le sache, que « annule et remplace » ne vise **que** le message choisi, et que chaque refus ou incertitude du serveur lui soit dit en clair.

### Périmètre

1. **Remise incertaine** reconnue (code et 502 brouillon), `detail` du serveur affiché, nouvelle tentative bloquée ; statut 0 et 504 traités comme incertains ; `deliveryUncertain` et `failedActionsCount` dans les modèles et l'écran des envois en attente.
2. **Annule et remplace** : contexte vidé à chaque ouverture qui n'est pas un remplacement ; `sendMailDirect` route aussi sur le contexte restauré d'un brouillon ; `warning` de la réponse affiché.
3. **Brouillon** : identifiant adopté seulement après une création réussie ; en cas d'échec, la rédaction reste ouverte et le médecin est prévenu ; sur 404 à l'envoi, envoi direct.
4. **Remplacement de la rédaction** : un seul chemin « enregistrer puis ouvrir » pour tous les déclencheurs ; `beforeunload` tant qu'il reste du contenu non enregistré.
5. **Pièces jointes** : transfert par référence (`sourceFolderPath/sourceUid/sourceOccurrence`, résolu par `OutgoingMailService`) plutôt que retéléchargement ; à défaut, `occurrence` transmis et Envoyer désactivé tant que des pièces sont en cours ; erreur de pièce visible jusqu'à une action explicite.
6. **Refus explicites** : `detail` affiché pour les 400 et 409 ; taille totale calculée avec les lectures en cours.
7. Corrections de **ANG-42 à ANG-44, ANG-46, ANG-75**.

> **⚠️ Arbitrage humain requis — le client mobile.** Le mobile rédige et envoie aussi (réponse, transfert,
> brouillons, envois en attente). Il n'a pas été audité. Inclure `client-mobile` (audit ciblé de la
> rédaction mobile dans le `/develop`), ou ouvrir une task mobile dédiée ?

## Definition of Done

- [ ] Build et tests verts : weda2, api-mail
- [ ] Tests unitaires et de composant rouges d'abord, client-angular :
  - [ ] 503 `MAIL_DELIVERY_UNCERTAIN` : message « peut-être parti », Envoyer bloqué ; même chose pour le 502 de la route brouillon, le statut 0 et le 504
  - [ ] « Annuler et remplacer » puis « Nouveau message » : l'envoi passe par `sendmail`, pas par `cancel-and-replace`
  - [ ] premier autosave en échec puis fermeture : la rédaction reste ouverte avec un message ; aucune requête PUT sur un identifiant jamais créé
  - [ ] clic sur un brouillon de la liste pendant une rédaction : la rédaction en cours est enregistrée avant d'être remplacée
  - [ ] transfert d'un mail à deux pièces homonymes : deux pièces distinctes envoyées ; Envoyer désactivé pendant leur récupération
  - [ ] adresse tapée sans Entrée puis Envoyer : elle est ajoutée (ou l'envoi est refusé avec un message) ; Cc/Cci non vides non masquables
  - [ ] un 409 d'opposition patient affiche le `detail` du serveur
  - [ ] appliquer un modèle en réponse conserve citation et signature
- [ ] Test d'intégration de bout en bout pour l'envoi d'un transfert par référence (`POST …/sendmail` avec pièces `sourceFolderPath/sourceUid/sourceOccurrence`) : les deux pièces homonymes d'origine sont dans le message remis (lu côté serveur de messagerie du test), vu rouge si l'occurrence est ignorée (règle 1b) — s'il n'existe pas déjà
- [ ] Scénarios E2E :
  - [ ] E2E-COMPOSE-004 « Une remise incertaine n'est jamais présentée comme un échec à renvoyer » ajouté (angular `requis`, mobile selon l'arbitrage)
  - [ ] E2E-DETAIL-001 versionné : le transfert d'un mail à deux pièces homonymes les envoie toutes deux
  - [ ] E2E-DRAFT-003 « Fermer une rédaction récente ne perd rien » ajouté
- [ ] Trou du filet : lignes dans `conventions/e2e.md`
- [ ] Aucune donnée de santé (corps, pièces) ajoutée aux journaux

## Manual Test Plan

1. Couper la connexion SMTP du serveur de test après DATA (banc) : l'écran dit « Ce message est peut-être parti… », Envoyer est bloqué.
2. « Annuler et remplacer » sur un envoi X, puis « Nouveau message » à un autre confrère, envoyer → X n'est pas marqué annulé.
3. Rédiger 10 s, cliquer sur un autre mail → le brouillon est enregistré ; rouvrir les brouillons : le texte est là.
4. Transférer un mail portant deux `document.pdf` différents → le confrère reçoit les deux documents.
5. Transférer un mail portant un IHE_XDM, cliquer aussitôt sur Envoyer → impossible tant que la pièce n'est pas jointe.
6. Patient opposé non acquitté : l'envoi affiche le motif du serveur.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif de l'envoi MSSanté
- **Exigences DSR honorées** : non applicable — rétablit la fiabilité de l'envoi (pas de doublon, pas d'envoi incomplet silencieux)
- **INS** : non applicable en écriture ; les documents transférés gardent leur identité (XDM inchangé)
- **Authentification PS** : PSC / e-CPS ; aucun envoi sans carte (règle inchangée : mise de côté puis confirmation)
- **Habilitations** : inchangées
- **Interop CI-SIS** : IHE XDM — les pièces d'origine sont transférées à l'identique, par référence
- **Tracé PGSSI-S** : envois, annulations (annule et remplace) et remises incertaines tracés comme aujourd'hui, désormais sur le bon message
- **Consentement patient** : opposition à l'envoi vers Mon Espace Santé — le refus du serveur est affiché
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé
