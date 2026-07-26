# todo-task-180.md — Identité des pièces jointes par nom de fichier : téléchargement du mauvais document, perte silencieuse

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe métier MSSanté).
> Finding vérifié sur pièces par le PO — voir « Preuve ».

## Objective

Donner aux pièces jointes une **identité stable et unique**, indépendante du nom
de fichier. Aujourd'hui une PJ est identifiée par son nom : deux pièces portant le
même nom dans un même message se confondent. Le praticien télécharge **le mauvais
document** — ou en perd un sans aucun message d'erreur.

Le cas n'est pas théorique : un laboratoire qui envoie deux analyses nommées
toutes deux `resultat.pdf` est un scénario courant, et la génération de noms côté
CDA produit elle-même des collisions (même catégorie, même patient, même date).

**US backend-only (justification)** : identité et résolution côté serveur. La route
de téléchargement évolue, mais l'API doit rester compatible (voir DOD).

### Preuve (état actuel du code)

- `src/Infrastructure/Repository/MailRepository.cs:1681` — résolution par nom :
  ```csharp
  var attachment = await DataContext.MailAttachments
      .FirstOrDefaultAsync(a => a.MailId == mailEntity.Id && a.FileName == attachmentFileName);
  ```
- `src/Infrastructure/Repository/MailRepository.cs:1705` — l'écriture retrouve la
  ligne **par nom** elle aussi : la mise à jour écrase le contenu de la *première*
  ligne avec les octets de la pièce qui vient d'être récupérée.
- `src/Application/Services/Implementation/ImapService.cs:1927-1928` — même
  résolution par nom côté IMAP (`summary.Attachments.FirstOrDefault(p => p.FileName == …)`).
- Route de téléchargement paramétrée par le nom : `…/download/attachment/{attachmentfilename}`.
- `src/Api/Controllers/V1/MailController.cs:548-568` — le ZIP ne lève l'ambiguïté
  que sur le **nom d'entrée** de l'archive, tout en récupérant les octets par le
  nom d'origine : l'archive contient `resultat.pdf` et `resultat (1).pdf` avec un
  contenu **identique**.
- `src/Infrastructure/Repository/MailRepository.cs:539` — côté CDA, la seconde
  pièce de même nom est purement et simplement **ignorée**
  (`if (!existingFileNames.Add(...)) continue;`).

À noter : l'entité `MailAttachment` porte **déjà** un `Guid` propre — l'identité
technique existe, elle n'est simplement pas utilisée pour la résolution.

### Contenu attendu

1. **Résolution par identifiant stable** (le `Guid` existant ou équivalent) sur
   tous les chemins : téléchargement unitaire, mise à jour du contenu, ZIP.
2. **Aucune perte silencieuse** : deux pièces de même nom dans un même message
   sont **deux pièces distinctes**, toutes deux stockées, listées et
   téléchargeables. Supprimer la logique qui écarte la seconde.
3. **Compatibilité de l'API** : les trois frontends utilisent la route par nom.
   Prévoir la transition (route par identifiant + conservation temporaire de la
   route par nom, qui doit alors se comporter de façon **déterministe** et non
   arbitraire) et documenter l'impact frontend dans la task — la bascule des
   clients fera l'objet d'une task dédiée par frontend.
4. **Noms d'affichage** : la désambiguïsation visuelle (`resultat (1).pdf`) reste
   utile pour le praticien et le ZIP — mais elle porte sur l'**affichage**, jamais
   sur l'identité.

### Hors scope

- La bascule des frontends vers la nouvelle route (une task par frontend).
- Les PJ absentes pour cause de MIME non standard → task-181.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire : un mail avec **deux** PJ de même nom et de contenus
      différents ⇒ deux entités distinctes persistées, contenus distincts (ce test
      doit échouer sur le code actuel — le vérifier explicitement)
- [ ] Test unitaire : le téléchargement de chacune des deux PJ renvoie **ses**
      octets (pas deux fois les mêmes)
- [ ] Test unitaire : la mise à jour du contenu d'une PJ n'écrase pas celui de sa
      homonyme
- [ ] Test d'intégration ZIP : l'archive contient deux entrées de noms distincts
      **et de contenus distincts**
- [ ] Test unitaire côté CDA : deux documents produisant le même nom généré sont
      tous deux conservés (plus de `continue` silencieux)
- [ ] Compatibilité vérifiée : les frontends actuels continuent de télécharger la
      bonne pièce dans le cas nominal (un seul fichier par nom)
- [ ] Impact frontend documenté dans la task (route cible, calendrier de bascule)
- [ ] Aucune donnée de santé en clair dans les logs (jamais de nom de fichier
      patient-identifiant journalisé au-delà de l'existant)

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. Envoyer vers la boîte de test un message avec **deux PJ homonymes** de contenus
   nettement différents (données anonymisées) : deux `resultat.pdf`, l'un
   contenant « ANALYSE A », l'autre « ANALYSE B ».
3. Synchroniser, ouvrir le message : **deux** pièces sont listées.
4. Télécharger la première → « ANALYSE A ». Télécharger la seconde → « ANALYSE B ».
   Avant correctif, les deux téléchargements donnent le même document.
5. « Télécharger tout » → l'archive contient deux fichiers de **contenus
   différents**. Avant correctif, les deux entrées sont identiques.
6. **Cas CDA** : envoyer un IHE_XDM contenant deux documents de même catégorie,
   même patient, même date (noms générés identiques) → les deux documents sont
   présents dans le dossier patient. Avant correctif, le second disparaît.
7. Non-régression : un message à PJ unique se télécharge exactement comme avant.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volet MSSanté
- **Exigences DSR honorées** : correctif de conformité — intégrité et complétude
  des documents reçus (PGSSI-S intégrité)
- **INS** : non applicable — l'identité patient n'est pas en cause ici (voir
  task-176), mais la **perte d'un résultat d'analyse** est un incident clinique
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : documents CDA r2 et archives IHE_XDM concernés en tant que
  contenu transporté ; parsing inchangé
- **Tracé PGSSI-S** : la journalisation du téléchargement de PJ est traitée par la
  task dédiée à la journalisation (voir task-186) ; ne pas la dupliquer ici
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé sur le plan du traitement — mais qualifier avec
  le humain le risque d'**exactitude** (art. 5.1.d) : un praticien a pu croire
  disposer d'un résultat qu'il n'avait pas.
