# task-397 — /review : CHANGES REQUESTED (2026-10-25)

Validation : build ✅ (0 erreur, 0 avertissement), tests ✅ (6 947 réussis, 0 échec, 16 ignorés),
Sonar ✅ (QG OK, 0 issue), e2e ✅ (mobile 46, angular 55, parité verte).

La revue de code (relecture indépendante, constats vérifiés dans le code) trouve **trois défauts
bloquants**, dont deux fuites de la règle 14 vers les journaux. Aucune PR n'est ouverte. Retour à
`/develop` pour corriger, puis `/sonar → /e2e → /review`.

## Bloquants

### B1 — Le puits de masquage ne masque que la propriété qui porte le chemin (fuite règle 14)

`src/Api/Telemetry/DelegatedLogMaskingSink.cs:77` : `Mask` ne réécrit un scalaire que s'il contient
lui-même `shared/…`. Une propriété **sœur** passe en clair :

- `MailController.cs:797` — `[DownloadAttachment] Start Folder={Folder}, …, Attachment={Attachment}`
  (Information) : `Folder` masqué, `Attachment` = nom de pièce jointe en clair, qui porte un nom de
  patient (constat M22 de la tranche 10).
- Noms de sous-dossiers délégués : `MailController.cs:2004` (`{Name}` à la création, parent = racine
  seule), `:2033` (`{NewName}`), `ImapFolderService.cs:337, 404, 409` ; `ImapService.cs:3714`
  (`{FileName}`, Debug).

**Pourquoi le test bout en bout ne l'a pas vu** (vert qui ment) : dans `UseCaseHttpHost`, les
journaux des **contrôleurs** passent par la journalisation Microsoft (`ServerErrorLog`), pas par
la capture Serilog derrière le puits de masquage. `TheWholeDelegatedJourney_…` n'observe donc que
les journaux des services de la fixture.

Correction attendue : dès qu'un événement porte un chemin délégué, masquer les propriétés sœurs
nominatives connues (`Attachment`, `FileName`, `Name`, `NewName`, `Subject`…) — ou ne plus les
journaliser sur un chemin délégué ; brancher le journal du serveur de test sur le même puits et la
même capture, et prouver la fuite rouge par le parcours.

### B2 — Les expressions de masquage s'arrêtent sur des caractères légaux d'un nom de dossier (fuite règle 14)

`src/Domain/Rules/DelegatedMailboxRule.cs:199-208` :
- `EncodedPath` arrête la queue à l'espace (`[^\s"'?&/]+`). `Request.Path` est décodé sauf `%2F` :
  `/folders/shared%2Fdr@x.fr%2FPatients Dupont/emails/12` → `…%2F… Dupont/emails/12`. Atteint
  l'attribut OTel `url.path`, `RequestLoggingMiddleware`, l'`instance` des ProblemDetails, le journal
  du limiteur de débit.
- `ClearPath` arrête la queue à `'` : `shared/a@b/Comptes rendus d'imagerie` → `…'imagerie`.

Correction attendue : masquer jusqu'au vrai délimiteur (`/emails`, `?`, fin de chaîne), tests sur
des noms avec espace et apostrophe.

### B3 — La borne d'entrées du cache J sature et ne se vide pas (décision 14 inopérante au-delà de 50)

`src/Application/Delegation/DelegatedContentCache.cs:113-133` : l'index par BAL ne retire jamais les
entrées **expirées**, son TTL est **renouvelé** à chaque écriture, et `MaxEntriesPerMailbox` (50) =
`MaxDelegatedDecodesPerEnrichment` (50). Un seul enrichissement d'une page remplit la borne ; ensuite
toute écriture est refusée tant que l'activité continue. Conséquences : en-têtes des pages
suivantes `Pending` pour toujours, chaque `enrich` redécode jusqu'à 50 messages (CPU), chaque
ouverture redécode. Lecture-puis-écriture non protégée de l'index : sous concurrence, des clés
perdues échappent à `RemoveMailboxAsync` (bornées par le TTL).

Correction attendue : index qui oublie ce qui a expiré (date d'expiration par entrée) et éviction
de la plus ancienne plutôt que refus ; test d'intégration au-delà de la borne.

## À corriger dans la même passe (non bloquant seul, coût faible)

- **S3 — dossier système suivi d'un `/`** : `RoleOf("Sent/")` → `Personal`, `IsCanonical` l'accepte ;
  `DELETE …%2FSent%2F` passe la politique ManageFolder. Impact non vérifié (Dovecot normalise-t-il ?) —
  refuser segments vides et séparateur final dans `IsCanonical` (404), par précaution : le risque est
  de vider les Envoyés du délégant.
- **S7 — suppression/renommage d'un dossier délégué** : le cache J n'est pas invalidé
  (`ImapFolderService.DeleteFolderAsync`) ; rien de périmé n'est servi, mais la section J dit
  « invalidé à la suppression ».
- **S8 — drapeaux périmés** : le contenu servi du cache garde `IsRead`/`IsFlagged` du décodage alors
  qu'un résumé frais est en main ; recopier les drapeaux du résumé.

## Suggestions (hors correction)

- S5 : la page d'en-têtes désérialise le `MailDto` complet du cache (jusqu'à 8 Mo, PDF compris) par
  message ; `WithLightDocuments` sérialise les octets avant de les vider → projeter légère à
  l'écriture, ou vider `Content` avant l'aller-retour JSON.
- S6 : enrichissement en mémoire = verrou + SELECT + FETCH par message, et `uids` non découpés en
  blocs dans `EnrichDelegatedInMemoryAsync`.
- S9 : l'abonnement SSE ne vérifie ni alias ni révocation (dossier en query string) ; faible, chaque
  publication revérifie.
- S10 : `Involves` (filtre) teste le préfixe `shared/`, `IsDelegated` exige un `@` : un
  `shared/<non-adresse>/…` passe le filtre et suit le code de la BAL propre. Échoue ouvert seulement
  si un serveur utilise `%%n` (Mailiz : `%%u`).

## Leçon (règle d'or)

Un test « rien dans les journaux » doit observer **tous** les producteurs de journaux du chemin testé,
contrôleurs compris : à consigner dans `conventions/csharp.md` avec la correction.
