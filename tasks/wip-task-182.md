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


## Branches

- `api-mail` (pushed) : `fix/task-182-dossiers-exclus-correspondance-exacte` —
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-182-dossiers-exclus-correspondance-exacte
- `dtos-mss` (pushed) : même nom — **auto-incluse**. Aucun changement de contrat attendu : si
  elle reste vide, aucune PR, suppression manuelle au merge (défaut de cycle, 4e occurrence
  attendue).

### ⚠️ État du code depuis la rédaction de la US (2026-07-25) — lu AVANT d'implémenter

**task-233 (mergée le 2026-08-05) a déjà fait une partie du travail, et pas le reste :**

- ✅ **La règle est déjà dite une seule fois** : `MailFolderNamingRule` (source unique), colonne
  générée PostgreSQL `Mails.IsInSentDraftOrTrashFolder`, consommée par les 7 sites de requête
  et par le contrôle en mémoire `IsSelfActionFolder`. La « Preuve (état actuel du code) » de la
  US — les blocs `ToLower().Contains` dupliqués — **n'existe plus sous cette forme**.
- ❌ **La sémantique de sous-chaîne, elle, est intacte** : l'expression de la colonne est
  `~ '(sent|draft|trash|corbeille|envoy|brouillon)'` **sans ancrage**. `Consentements`
  matche `sent` : **le bug clinique est toujours là**, simplement concentré en un seul endroit
  au lieu de huit. Le travail de cette task est de changer la sémantique de cet endroit unique.
- 📌 **L'arbitrage produit demandé par task-233 est tranché par cette US** : task-233 avait
  renvoyé au PO la question « union SPECIAL-USE + nom ? » ; cette US, écrite avant, y répond
  oui (attributs quand fournis, repli sur correspondance exacte).
- ⚠️ **Conséquence pratique** : changer la règle = **migration** (une colonne générée ne
  s'`ALTER` pas — DROP + ADD, recalcul de toute la table) + mise à jour du modèle EF + des
  tests de task-233 qui caractérisent la sémantique actuelle.

Pré-flight vert sur les six repos mesurables. Dépendances : aucune.


## Develop log

Un seul commit applicatif : `8e6e065` sur `fix/task-182-dossiers-exclus-correspondance-exacte`.

### Preuve ROUGE avant correctif — l'exigence explicite du DOD

La théorie de la colonne, étendue aux victimes, échoue sur la règle actuelle : **4 échecs,
exactement** `Consentements`, `Renvoyés`, `Présentations`, `Documents envoyés par le patient`.

**Correction au diagnostic de la US** : `Absences`, cité comme victime, ne l'était pas —
« absences » ne contient aucun jeton (s-e-n-**c**). Il reste dans les tests comme cas conservé.

### La sémantique retenue : le segment, pas la sous-chaîne

Chemin découpé sur `/` et `.`, chaque segment comparé **exactement** (insensible à la casse) à
une liste de noms connus élargie aux variantes réelles des serveurs (`Sent Items`,
`Sent Mail`, `Éléments envoyés`, `Deleted Items`…, graphies accentuée **et** non accentuée —
`unaccent()` n'est pas immuable au sens PostgreSQL, donc interdit dans une colonne générée).
`Sent/2024` reste exclu (sous-dossier de même nature), `[Gmail]/Sent Mail` aussi. Le
séparateur `.` est inclus parce que **Dovecot en Maildir sépare par défaut avec `.`** — le
banc en dépend ; coût assumé : un dossier nommé « x.sent.y » serait exclu à tort, cas jugé
bien plus rare que les victimes réelles.

### SPECIAL-USE : l'union, et l'écart assumé avec la lettre de la US

La US demande que les attributs **priment** sur le nom. Implémenté en **union** — le type ne
peut qu'**ajouter** des exclusions, jamais en retirer — parce que task-233 a observé la
classification persistée **transitoirement fausse** (un vrai `Trash` classé `Custom` pendant
une fenêtre) : « primer » dans les deux sens aurait, pendant une telle fenêtre, fait entrer la
corbeille dans les dossiers patients. Trois tests fixent les trois quadrants ; **preuve ROUGE
de la jambe type** : liste des types neutralisée → seul le test « nom inconnu classé Sent »
tombe, le plancher par nom tient.

### La règle était en QUATRE exemplaires, pas un

task-233 l'avait centralisée côté Infrastructure — mais `ImapService` et
`BackgroundEnrichmentProcessor` (couche Application, qui **ne peut pas** référencer
Infrastructure) gardaient chacun leur copie de sous-chaîne. Le commentaire de `MailRepository`
disait « si un troisième appelant apparaît, promouvoir en helper partagé » : **les troisième
et quatrième existaient déjà**. La règle vit désormais dans **Domain**, seule couche visible
des trois consommatrices.

**Conséquence fonctionnelle au-delà de la restitution** : ces deux copies gardaient
l'enrichissement — un message rangé dans `Consentements` n'était pas seulement caché du
dossier patient, il n'était **jamais analysé**. Il est désormais enrichi comme les autres.

### Vérification du périmètre (item 4 de la US) — les consommateurs, tous listés

| Consommateur | Sémantique appliquée |
|---|---|
| Colonne générée `Mails.IsInSentDraftOrTrashFolder` | nom exact par segment (plancher) |
| `PatientRepository` — 3 sites (page dossier patient, réfs de doublons, membres de cluster) | plancher **+ union SPECIAL-USE** |
| `MailRepository` — 4 sites (doublon exact, versions de lot, docs d'origine, original du doublon) | plancher **+ union SPECIAL-USE** |
| `MailRepository.IsSelfActionFolder` (mémoire — détection au vol) | nom exact seul (pas d'accès au type persisté, documenté) |
| `ImapService.IsSelfActionFolder` (mémoire — enrichissement) | idem |
| `BackgroundEnrichmentProcessor.IsSelfActionFolder` (mémoire) | idem |

### Migrations (audit règle 7c)

- `20260806120000` — DROP + ADD de la colonne générée (PostgreSQL ne modifie pas l'expression
  d'une colonne générée). Le ADD **recalcule toutes les lignes** : les documents déjà rangés
  dans un `Consentements` redeviennent visibles **dès la migration**, sans réanalyse. `Down`
  restaure l'expression historique à l'identique.
- `20260805130000` (task-233) — **figée** à son expression historique : une migration déjà
  appliquée ne change pas de comportement rétroactivement ; elle référençait la constante
  partagée, qui vient de changer de valeur et de couche.
- Numéro strictement postérieur aux six existants, aucune collision ; pas de snapshot EF ;
  modèle et migration partagent la même constante.

### Validation

Build 0 erreur / 0 avertissement · domain 136/136 · infrastructure 419/419 ·
application 1998/1998 · api 650/650 · integration **362/362** (16 ignorés). Un flaky sans
rapport (`FlagsmithFeatureFlagServiceTests.RefreshFailure_LogsOncePerWindow`, fenêtre
temporelle) rouge sur un run, vert au suivant.

Les semeurs de tests qui s'isolaient par suffixe (`Sent_T233_xyz`) passent en forme
sous-dossier (`Sent/T233-xyz`) : l'isolation par suffixe **reposait sur la sémantique de
sous-chaîne** — y compris un oublié (`Envoyés_T233_`) attrapé par la suite d'intégration.

### Ce qui reste au Manual Test Plan (humain)

Les étapes 2-7 de la US — dossier `Consentements` réel dans la boîte MSSanté de test, dépôt
d'un CDA, vérification visuelle. Non automatisables ici : elles exigent la boîte réelle.
