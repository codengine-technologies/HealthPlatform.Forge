# todo-task-181.md — Pièces jointes et archives IHE_XDM invisibles quand l'émetteur omet `Content-Disposition`

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe métier MSSanté).

## Objective

Ne plus perdre de pièce jointe à cause de la **forme MIME** du message émetteur.
Toute la surface « pièces jointes » dérive aujourd'hui d'une seule source qui ne
retient que les parties portant un en-tête `Content-Disposition` non `inline`. Une
ordonnance envoyée sans cet en-tête — forme courante depuis certaines passerelles
et messageries anciennes — est **totalement invisible** : le praticien voit un
message vide, sans aucun moyen d'accéder au document.

Le même filtre gouverne la détection de l'archive `ihe_xdm.zip` : un message dont
l'archive n'est pas déclarée en `attachment` ne produit **aucun** document médical,
aucun lien patient, aucun marqueur biologie. Le message ressemble à une simple
notification.

**US backend-only (justification)** : extraction MIME côté serveur, contrats
inchangés.

### Preuve (état actuel du code)

- `src/Application/Helpers/EmailAddressHelper.cs:55-63` — `ExtractAttachments(summary.Attachments)`
  est l'**unique** producteur de `MailDto.Attachments`. `summary.Attachments`
  (MailKit) ne retourne que les parties à `Content-Disposition` non `inline`.
- `src/Application/Services/Implementation/IheXdmProcessingService.cs:27-28` —
  la détection de l'archive est filtrée de la même façe :
  `summary.Attachments.Any(p => p.FileName.Equals("ihe_xdm.zip", …))`.
- Aucune inspection de `summary.BodyParts` nulle part dans `src/`, et aucun
  traitement des parties `inline` / `cid:` (le sanitizer HTML conserve pourtant
  les URL `cid:`, d'où une image cassée à l'affichage).
- Asymétrie émission / réception : l'envoi accepte `ihe-xdm.zip` **et**
  `ihe_xdm.zip` (`src/Application/Services/Implementation/MssanteHeaderService.cs:38`),
  la réception exige exactement `ihe_xdm.zip` — un `IHE-XDM.zip` entrant est ignoré.

### Contenu attendu

1. **Détection élargie des pièces jointes** : une partie MIME porteuse d'un nom de
   fichier (via `Content-Type; name=` ou `Content-Disposition; filename=`) et non
   destinée à l'affichage inline doit être traitée comme pièce jointe, même sans
   `Content-Disposition`. S'appuyer sur MimeKit plutôt que sur des heuristiques
   maison.
2. **Détection de l'archive IHE_XDM robuste** : reconnaître l'archive
   indépendamment de la casse et du séparateur (`ihe_xdm.zip`, `ihe-xdm.zip`,
   `IHE_XDM.ZIP`), en alignant réception et émission.
3. **Parties inline** : une image ou un document `inline` référencé par `cid:` doit
   être soit rendu correctement dans le corps, soit exposé comme pièce jointe
   accessible — jamais une image cassée sans recours. Le comportement retenu doit
   être documenté dans la task.
4. **`message/rfc822`** : un mail transféré en pièce jointe doit être
   téléchargeable. Aujourd'hui `DownloadAttachmentMimePartAsync`
   (`src/Application/Services/Implementation/ImapService.cs:1931-1939`) se termine
   par `return entity as MimePart;` — or une partie `message/rfc822` se
   désérialise en `MessagePart`, qui **n'est pas** un `MimePart` : le cast donne
   `null` et le téléchargement échoue systématiquement (« Attachment content is
   null »), le ZIP l'ignore en silence.
5. **Aucune perte muette** : si une partie ne peut pas être traitée, cela doit être
   **visible** (journalisé côté serveur, et signalé au praticien) plutôt que
   silencieusement absent de la liste.

### Hors scope

- L'identité des PJ homonymes → task-180.
- Le rendu HTML du corps au-delà du cas `cid:`.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire : message avec une partie `application/pdf; name="Ordonnance.pdf"`
      **sans** `Content-Disposition` ⇒ la PJ est listée et téléchargeable (ce test
      doit échouer sur le code actuel — le vérifier explicitement)
- [ ] Test unitaire : archive nommée `IHE-XDM.zip` / `IHE_XDM.ZIP` ⇒ documents
      médicaux extraits comme pour `ihe_xdm.zip`
- [ ] Test unitaire : archive IHE_XDM **sans** `Content-Disposition` ⇒ documents
      extraits, lien patient et marqueur biologie posés
- [ ] Test unitaire : PJ `message/rfc822` (mail transféré) ⇒ téléchargement réussi,
      et présence dans le ZIP
- [ ] Test unitaire : image `inline` référencée en `cid:` ⇒ comportement conforme
      à la décision documentée (rendue ou exposée), jamais une image cassée
- [ ] Test de non-régression : un message MIME standard (PJ en `attachment`)
      conserve exactement le comportement actuel
- [ ] Toute partie non traitée est journalisée côté serveur (sans contenu ni nom
      patient-identifiant) et n'est jamais silencieusement omise
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. **PJ sans `Content-Disposition`** : envoyer vers la boîte de test un message
   forgé avec `Content-Type: application/pdf; name="Ordonnance.pdf"` et
   `Content-Transfer-Encoding: base64`, sans `Content-Disposition` (données
   anonymisées). Synchroniser → la PJ apparaît et s'ouvre. Avant correctif : le
   message paraît vide.
3. **Archive IHE_XDM non standard** : même exercice avec une archive nommée
   `IHE-XDM.zip` → les documents médicaux sont créés, le patient rattaché, le
   marqueur biologie posé si applicable.
4. **Mail transféré** : transférer un message en pièce jointe (`.eml`) vers la
   boîte → la PJ se télécharge et s'ouvre dans un client mail. Avant correctif :
   erreur générique à chaque tentative.
5. **Image inline** : envoyer un message HTML avec une image `cid:` → l'image
   s'affiche (ou est accessible en PJ), sans image cassée.
6. **Non-régression** : un message MSSanté ordinaire avec PJ classique et
   `ihe_xdm.zip` se comporte comme avant.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volet MSSanté, réception des documents de santé
- **Exigences DSR honorées** : correctif de conformité — complétude de la
  réception MSSanté (une pièce reçue doit être restituée au praticien)
- **INS** : indirectement concerné — une archive IHE_XDM ignorée signifie **aucun**
  rattachement patient pour les documents qu'elle porte
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : cœur du sujet — archives IHE_XDM et documents CDA r2 ;
  parsing et validation Schematron via `interop-cda` inchangés, seule la détection
  des parties MIME évolue
- **Tracé PGSSI-S** : journaliser toute partie MIME non traitée (évènement
  technique, sans contenu) — c'est le filet qui rend la perte détectable
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé — pas de nouveau traitement ; qualifier
  toutefois avec le humain le risque clinique d'ordonnances et de comptes-rendus
  jamais restitués.
