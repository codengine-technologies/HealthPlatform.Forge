# todo-task-182.md — Dossiers exclus par test de sous-chaîne : « Consentements » est traité comme « Sent »

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe métier MSSanté).
> Finding vérifié sur pièces par le PO.

## Objective

Identifier les dossiers « d'auto-action » (Envoyés, Brouillons, Corbeille) par une
règle **exacte** plutôt que par une recherche de sous-chaîne dans le chemin.

La règle actuelle exclut tout dossier dont le chemin **contient** `sent`, `draft`,
`trash`, `corbeille`, `envoy` ou `brouillon`. Conséquence directe et vérifiée :
un dossier `Consentements` contient la sous-chaîne `sent`
(`con**sent**ements`) — **tous les documents qu'il contient disparaissent du
dossier patient**. Le praticien ouvre le dossier du patient, ne voit aucun
consentement, et en conclut qu'il n'a jamais été reçu.

Autres noms français touchés : `Absences`, `Présentations`, `Renvoyés`,
`Documents envoyés par le patient`…

**US backend-only (justification)** : règle de filtrage côté serveur.

### Preuve (état actuel du code)

`src/Infrastructure/Repository/PatientRepository.cs:210-215` — filtre des
documents du dossier patient :
```csharp
.Where(d => !d.Mail!.FolderPath!.ToLower().Contains("sent")
            && !d.Mail.FolderPath.ToLower().Contains("draft")
            && !d.Mail.FolderPath.ToLower().Contains("trash"))
.Where(d => !d.Mail!.FolderPath!.ToLower().Contains("corbeille")
            && !d.Mail.FolderPath.ToLower().Contains("envoy")
            && !d.Mail.FolderPath.ToLower().Contains("brouillon"))
```

La même liste de jetons est dupliquée à trois autres endroits :
- `src/Infrastructure/Repository/PatientRepository.cs:408-413` (liste des mails du
  patient) ;
- `src/Infrastructure/Repository/MailRepository.cs:2812-2819` et `:2830-2837`
  (détection de doublons — donc la détection ne fonctionne pas non plus dans ces
  dossiers).

### Contenu attendu

1. **Identification fiable des dossiers spéciaux** : s'appuyer sur les attributs
   IMAP `\Sent`, `\Drafts`, `\Trash` (SPECIAL-USE, RFC 6154) quand le serveur les
   fournit, avec repli sur une correspondance **exacte** de noms connus (et non
   une sous-chaîne).
2. **Règle unique et partagée** : une seule implémentation, consommée par les
   quatre emplacements. La duplication actuelle garantit la divergence.
3. **Insensibilité à la casse et aux accents** conservée sur la correspondance
   exacte (`Envoyés`, `envoyes`, `ENVOYÉS`).
4. **Vérification du périmètre** : lister dans la task tous les usages de la règle
   et confirmer que chacun applique bien la sémantique voulue.

### Hors scope

- La configuration par l'utilisateur du mapping de ses dossiers spéciaux
  (amélioration produit possible, à arbitrer séparément).

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire paramétré **anti-faux-positif** : `Consentements`, `Absences`,
      `Présentations`, `Renvoyés` ne sont **pas** des dossiers d'auto-action (ce
      test doit échouer sur le code actuel — le vérifier explicitement)
- [ ] Test unitaire paramétré **vrai positif** : `Sent`, `Envoyés`, `INBOX/Drafts`,
      `Brouillons`, `Trash`, `Corbeille` sont bien identifiés
- [ ] Test unitaire : les attributs IMAP SPECIAL-USE priment sur le nom quand ils
      sont disponibles
- [ ] Test d'intégration : un document CDA reçu dans un dossier `Consentements`
      apparaît bien dans le dossier patient
- [ ] La règle est implémentée **une seule fois** et les quatre emplacements la
      consomment (vérifié : plus aucune liste de jetons dupliquée)
- [ ] Non-régression : la détection de doublons continue d'ignorer les vrais
      dossiers Envoyés / Brouillons / Corbeille
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. Dans la boîte MSSanté de test, créer un dossier **`Consentements`**.
3. Y déposer (ou y déplacer) un message porteur d'un document CDA rattaché à un
   patient de test (données anonymisées). Synchroniser.
4. Ouvrir le dossier du patient. **Attendu** : le document du dossier
   `Consentements` est présent. Avant correctif, il est absent — sans aucun
   message d'erreur.
5. Répéter avec un dossier `Absences` et un dossier `Renvoyés`.
6. **Non-régression** : déposer un message dans le vrai dossier `Envoyés` → il
   reste exclu du dossier patient, comme aujourd'hui. Idem `Corbeille` et
   `Brouillons`.
7. Vérifier que la détection de doublons fonctionne dans `Consentements` (un
   document identique reçu deux fois y est bien signalé comme doublon).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volet MSSanté
- **Exigences DSR honorées** : correctif de conformité — complétude du dossier
  patient restitué au praticien
- **INS** : non applicable — le rattachement patient n'est pas en cause, seule la
  **restitution** l'est
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : documents CDA r2 concernés en tant que contenu filtré ;
  parsing inchangé
- **Tracé PGSSI-S** : non applicable — pas de nouvel évènement à journaliser
- **Consentement patient** : **pertinence directe** — les documents de consentement
  patient sont précisément ceux que le défaut fait disparaître, ce qui peut nuire
  à la traçabilité d'un consentement pourtant reçu
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé — pas de nouveau traitement ; risque
  d'exactitude/complétude (art. 5.1.d) à mentionner au humain.
