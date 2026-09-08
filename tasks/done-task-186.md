# todo-task-186.md — Journal d'audit PGSSI-S : sorties de PJ non imputables, traces perdues sous charge, actions inconnues mal étiquetées, aucune politique de conservation

**Repos**: api-mail, dtos-mss, client-blazor, client-angular
**Dependencies**: —
**Epic**: E009
**Single frontend**: false

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axes confidentialité
> et concurrence). Vérifié par le PO.

> ### Re-vérification du 2026-08-23 — **toujours pertinente, intégralement**
>
> Chaque preuve rejouée sur `develop`. Les numéros de ligne du bloc « Preuve »
> datent du 2026-07-25 ; **la colonne « au 2026-08-23 » fait foi**.
>
> | Preuve | 2026-07-25 | Au 2026-08-23 | État |
> |---|---|---|---|
> | PJ unitaire non tracée | `MailController.cs:437` | **`:505`** (`…/download/attachment/{attachmentfilename}`) | inchangé |
> | Archive ZIP non tracée | `:495-570` | **`:592`** (`…/attachments/download/zip`) | inchangé |
> | `MailController` n'appelle jamais l'audit | — | **confirmé : 0 occurrence** de `auditService`/`IAuditService` dans le fichier | inchangé |
> | Aucun type d'action « pièce jointe » | énumération | **confirmé** — `Dtos/AuditActionType.cs` (le type vit dans `dtos-mss`) n'a **aucun** membre `Attachment*`/`*Download*` | inchangé |
> | Asymétrie avec l'export | `MailExportController.cs:142-154` | **`:88`** (EML) et **`:124`** (PDF/impression) tracent, via `TraceMailAction` | inchangé |
> | File bornée qui jette le plus ancien | `ServiceCollectionExtensions.cs:90-93` | **`:125-127`** — `BoundedChannelOptions(1000)` + `FullMode = DropOldest` | inchangé |
> | Retour de `TryWrite` ignoré | `AuditService.cs:45` | **`:59`** | inchangé |
> | Contrat inverse documenté | `AuditBackgroundService.cs:15` | **`:14`** (« no trace is lost ») et `:45`, `:48` (« the trail must be exhaustive ») | inchangé |
>
> **Note de périmètre découverte à la re-vérification** : le type d'action vivant
> dans `dtos-mss`, ajouter des membres à `AuditActionType` **touche un porteur de
> contrat** — la task devra lister `dtos-mss` dans `**Repos**:` et passer par
> `/publish-dtos`. Ce point n'était pas identifié au 2026-07-25.

> ### Revue du 2026-09-07 — reformulation, défauts 3 et 4 ajoutés, périmètre frontends
>
> Positions confirmées sur `develop` : endpoints à **`MailController.cs:506`** et
> **`:593`**, `AuditActionType` sans membre `Attachment*`,
> **`ServiceCollectionExtensions.cs:131`** (`CreateBounded(1000)`) / **`:133`**
> (`DropOldest`), **`AuditService.cs:59`** (`TryWrite` ignoré), **13 fichiers**
> appelant `auditService.Trace` (aucun n'est `MailController`).
>
> Cinq changements par rapport à la rédaction initiale :
>
> 1. **L'objectif est reformulé.** La rédaction précédente (« quiconque détenant
>    un jeton valide peut exfiltrer… ») laissait croire à une faille de contrôle
>    d'accès. Il n'y en a pas : `GetAttachmentStreamAsync` passe par la session
>    IMAP du praticien, on n'accède qu'à sa propre boîte. Le défaut porte sur
>    **l'imputabilité**, pas sur l'authentification ni sur l'autorisation.
> 2. **Un troisième défaut est intégré** : aucune politique de conservation
>    n'existe (0 occurrence de purge/rétention sur `MssAuditTrace`, aucune section
>    `Audit` dans les `appsettings.json`). La table croît indéfiniment. Ce point
>    était rangé en « Hors scope » ; une durée de conservation non fixée est
>    elle-même un défaut de conformité (RGPD art. 5.1.e).
> 3. **L'INS dans le journal d'audit est tranché** (humain, 2026-09-07) : il y a
>    sa place, et il n'y a **pas** sa place dans les logs. Voir l'encadré dédié —
>    la section conformité affirmait l'inverse, elle est corrigée.
> 4. **La task n'est PAS backend-only** — corrigé après inventaire (2026-09-07).
>    Un **journal d'audit consultable existe déjà** dans deux frontends
>    (`client-blazor` et `client-angular`), avec filtre par type d'action et
>    libellés par action. Ajouter deux `AuditActionType` les impacte donc
>    directement. `**Repos**` passe de `api-mail, dtos-mss` à
>    `api-mail, dtos-mss, client-blazor, client-angular` ; `**Single frontend**`
>    passe à `false`. **`client-mobile` n'est pas impacté** (0 occurrence
>    d'« audit » dans `Client/Mobile/src`). Voir la section « Impact frontends ».
> 5. **Un quatrième défaut est intégré** (relecture critique du 2026-09-07) : la
>    relecture d'une action inconnue retombe silencieusement sur `ImapConnect`.
>    La même relecture a corrigé quatre points où la spec demandait ce que le code
>    ne permet pas : purge « par base praticien » sans **aucune énumération des
>    tenants** ni bibliothèque cron dans le repo ; attente asynchrone bornée
>    depuis `IAuditService.Trace` qui est **`void` synchrone** ; « aucun
>    changement de DTO » incompatible avec « la valeur inconnue reste lisible » ;
>    « la purge se trace elle-même » sans type d'action ni acteur — et avec le
>    filtre `UserId == Email` de `GetTracesAsync`, une trace « system » serait
>    **invisible** dans les écrans. Chaque point est tranché dans le corps.

## Objective

Rendre le journal d'audit **complet, fiable et borné dans le temps**, c'est-à-dire
réellement opposable. Quatre défauts se composent, et ils se renforcent l'un
l'autre.

### Ce dont il ne s'agit pas

**Ce n'est pas un défaut de contrôle d'accès.** L'accès aux pièces jointes passe
par la session IMAP du praticien authentifié (PSC / e-CPS) : un porteur de jeton
n'atteint que sa propre boîte. Les trois piliers se lisent ainsi :

| Pilier | Question | État |
|---|---|---|
| Authentification | Qui es-tu ? | OK (PSC / e-CPS) |
| Autorisation | As-tu le droit ? | OK (boîte propre) |
| **Imputabilité** | **Qui a fait quoi, quand ?** | **défaillante** |

La task porte **uniquement sur le troisième pilier**. Ce que la journalisation
couvre, et qu'aucun contrôle d'accès ne peut couvrir :

- **l'usage abusif par un utilisateur parfaitement légitime** — praticien qui
  extrait en masse les PJ de sa boîte avant de quitter le cabinet, remplaçant,
  carte confiée à un tiers du cabinet. Jeton valide, accès autorisé, comportement
  anormal ;
- **l'usage d'une session détournée** — poste non verrouillé, infostealer,
  extension de navigateur, jeton fuité (cf. task-184). « Valide » signifie signé
  et non expiré, pas « présenté par la bonne personne ».

La trace ne prévient rien : elle rend l'évènement **reconstituable** — détection
a posteriori sur volumétrie anormale, preuve en cas de plainte patient ou de
contrôle CNIL, et symétriquement capacité à **innocenter** un praticien mis en
cause.

### Défaut 1 — Trou de couverture (asymétrie)

Les deux routes qui extraient des pièces jointes cliniques brutes de la plateforme
(PJ unitaire, archive ZIP) ne produisent **aucune** trace, alors que l'export PDF,
l'impression et l'export EML du **même message** en produisent une. Ce sont
fonctionnellement **la même opération** : faire sortir un document de santé de la
plateforme. Deux traitements opposés pour un même évènement — c'est un oubli, pas
un arbitrage. C'est cette asymétrie qui rend le journal non opposable : il prétend
couvrir les sorties de données de santé, il en couvre la moitié.

### Défaut 2 — Perte silencieuse sous charge (et effacement d'historique)

Le canal d'audit est borné à 1000 en `FullMode = DropOldest`, et l'écriture ignore
sa valeur de retour. Deux conséquences distinctes :

- dès que l'écriture dépasse la lecture, des traces **déjà acceptées** sont
  écartées — sans log, sans métrique, sans erreur ;
- `DropOldest` fait disparaître **l'historique** sous la pression du présent.
  Quiconque peut générer du volume de traces (une synchronisation de boîte
  volumineuse suffit — aucun privilège particulier) peut faire disparaître les
  1000 traces précédentes. C'est un effacement de piste d'audit accessible sans
  privilège, donc un vecteur anti-forensique — et il dévalue aussi les traces
  correctement écrites, puisqu'un journal qui peut être vidé silencieusement n'a
  plus de valeur probante.

### Défaut 3 — Aucune politique de conservation

Vérifié le 2026-09-07 : **aucune purge, aucune durée de rétention** sur
`MssAuditTrace` (0 occurrence dans le code, aucune section `Audit` dans les
`appsettings.json`). La table croît indéfiniment, sur chaque base praticien. Une
durée de conservation non fixée est un défaut de conformité en soi (RGPD art.
5.1.e, minimisation), et l'absence de purge finit par peser sur la base même dont
le ralentissement provoque le défaut 2.

### Défaut 4 — Une action inconnue est mal étiquetée, silencieusement

Découvert à l'inventaire du 2026-09-07, et directement déclenché par cette task.
`src/Infrastructure/Repository/AuditTraceRepository.cs:246-249` :

```csharp
private static AuditActionType ParseActionType(string? value)
{
    return Enum.TryParse<AuditActionType>(value, out var result) ? result : AuditActionType.ImapConnect;
}
```

La colonne `MssAuditTrace.ActionType` est un **texte** ; la relecture reparse ce
texte vers l'enum. Un nom d'action que le binaire lecteur ne connaît pas retombe
donc sur **`ImapConnect` (ordinal 0)** — sans log, sans erreur. Une trace
« téléchargement de pièce jointe » s'affiche « Connexion IMAP ». C'est pire
qu'une trace absente : elle est **présente et fausse**, ce qui contamine
l'exploitation du journal au lieu de simplement la trouer.

Le cas devient réel dès cette task, dans deux situations banales : une instance
non redéployée relisant des traces écrites par une instance à jour, et un
consommateur épinglé sur une version antérieure du paquet `dtos-mss`.

Ensemble : un journal qui a des trous par oubli, d'autres trous par conception
qu'il ne signale pas, des étiquettes fausses quand il ne reconnaît pas une
action, et aucune borne de conservation.

**Périmètre** : le cœur est backend, mais **le journal d'audit est déjà exposé à
l'utilisateur** — `GET api/v1/Audit/traces` (`AuditController.cs:30`), écran
Blazor `Src/Modules/Mss/Plugin/Pages/Audit.razor` (« Journal d'audit »,
`MailModule.cs:46-49`), écran Angular `libs/mss/src/features/audit/`. Deux
nouveaux types d'action ne sont donc pas invisibles : ils doivent être
**lisibles et filtrables** dans ces deux écrans, sinon la trace existe en base
mais reste hors de portée de celui qui en a besoin. `client-mobile` n'a aucun
écran d'audit et n'est pas touché.

### Preuve (état actuel du code)

**Trou de couverture** :
- `src/Api/Controllers/V1/MailController.cs:506` (PJ unitaire) et `:593` (archive
  ZIP) : `MailController` n'appelle **jamais** `auditService.Trace` — il est
  absent des treize fichiers qui le font.
- L'énumération `AuditActionType` (dans `dtos-mss`) n'a **aucun** membre relatif
  aux pièces jointes (les valeurs existantes couvrent `MailRead`, `MailExportPdf`,
  `MailExportEml`, `MailPrint`, `MailSend`, …).
- Asymétrie révélatrice : `src/Api/Controllers/V1/MailExportController.cs:88`
  (EML) et `:124` (PDF / impression) journalisent via `TraceMailAction`.

**Perte silencieuse** :
- `src/Application/Extensions/ServiceCollectionExtensions.cs:131-133` :
  ```csharp
  services.AddSingleton(Channel.CreateBounded<MssAuditTrace>(new BoundedChannelOptions(1000)
  {
      FullMode = BoundedChannelFullMode.DropOldest
  }));
  ```
- `src/Application/Services/Implementation/AuditService.cs:59` :
  `_channel.Writer.TryWrite(trace);` — valeur de retour **ignorée**.
- `src/Application/Services/Implementation/AuditBackgroundService.cs:14` documente
  pourtant le contrat inverse : « PGSSI-S : no trace is lost — the remainder of the
  channel is drained and persisted at shutdown ». Le drainage ne protège que
  l'arrêt, **pas** la contre-pression.

Déclencheur réaliste : la base ralentit (ou une base praticien est injoignable, et
`PersistBatchAsync` retombe sur `PersistIndividuallyAsync` — un scope et un
aller-retour par trace). Pendant que le lecteur est bloqué, une synchronisation
d'arrière-plan continue de tracer des milliers de messages. Au-delà de 1000, les
plus anciennes disparaissent.

**Absence de conservation** :
- Aucun service de purge, aucune option de rétention : une recherche
  `retention|purge|conservation` sur `src/` ne remonte que du cache mail, des
  connexions SMTP et de la maintenance mail — rien sur l'audit.
- `src/Api/appsettings*.json` : aucune section `Audit`.

## Contenu attendu

### 1. Couvrir le téléchargement de pièces jointes

Nouveaux membres `AuditActionType` — **appendus en fin d'énumération** (le format
de sérialisation est l'ordinal entier ; toute insertion au milieu décale
silencieusement l'étiquette de toutes les traces historiques côté consommateur) :

- `AttachmentDownload` — téléchargement unitaire ;
- `AttachmentsDownloadZip` — archive de toutes les PJ d'un message.

Tracés comme le sont déjà l'export PDF/EML — **qui, quoi, quand, pour quel
patient** — mais **sans contenu clinique** (ni corps de message, ni contenu de
document, ni résultat). Le contexte patient (`PatientIns`, `DocumentId`,
`DocumentCategory`) est renseigné quand il est disponible : c'est ce qui rend la
trace exploitable en litige (cf. l'arbitrage tranché plus bas). Passage par
`/publish-dtos` (porteur de contrat).

**Moment de la trace et sens de `Success` — tranché par symétrie.**
`MailController.cs:506` rend un `FileStreamResult` : l'écriture au client a lieu
**après** le retour de l'action (cf. task-252, `AttachmentDownloadScope`). On
applique **exactement la règle de `MailExportController.TraceMailAction`
(`:147-161`)** : la trace est émise **après la résolution réussie de la
ressource, avant `return File(...)`**, avec `Success = true` ; aucune trace n'est
émise quand la résolution échoue (404, dossier introuvable), comme l'export
n'en émet pas. « Tracé » signifie donc *la sortie a été autorisée et engagée*,
pas *le client a reçu le dernier octet* — information que le serveur ne détient
de toute façon pas de manière fiable. Ne **pas** raccrocher la trace à
`Response.OnCompleted` : ce rappel n'a plus de scope DI utilisable, et
`AuditService` est scoped.

Pour la variante ZIP, une seule trace pour l'archive, `AttachmentCount` = nombre
de PJ empaquetées.

### 1bis. Impact frontends — le journal est déjà consultable

Inventaire du 2026-09-07. Le contrat `AuditActionType` est **partagé et
dupliqué** : une énumération C# dans `dtos-mss`, un miroir TypeScript dans
`client-angular`. C'est là que se situe tout le risque.

| Emplacement | Existe ? | Comportement sur une valeur nouvelle | Action requise |
|---|---|---|---|
| `Dtos/AuditActionType.cs` (v285.0.0, `PackageReference` × 7) | oui, 28 membres (0..27) | — | **append 28, 29, 30** + sentinel **`Unknown = -1`** + `/publish-dtos` + bump consommateurs |
| `Dtos/MssAuditTraceDto.cs` | oui | — | **un champ additif** `ActionTypeName` (string, nom brut persisté) — cf. §4bis |
| Backend `AuditController.cs:30` + `AuditTraceRepository.cs:132-136` | oui | filtre `ActionType.ToString()` sur colonne texte | **rien** — fonctionne d'emblée |
| Migration EF | — | colonne `ActionType` = `string` | **aucune** (pour l'enum ; l'index `Timestamp` du §5 reste dû) |
| Blazor `Audit.razor:51-60` (dropdown) | oui | `Enum.GetValues<AuditActionType>()` → **auto** | **exclure `Unknown`** du déroulant (filtrer sur un sentinel n'a pas de sens) |
| Blazor `Audit.razor:319-337` (`ActionLabels`) | oui, **16 entrées sur 28** ; `private static` dans la page | fallback `type.ToString()` → « AttachmentDownload » en anglais brut | **extraire** dans une classe statique testable, **compléter à 32**, alignés sur Angular (cf. tableau) |
| Angular `audit.model.ts:7-37` (enum TS) | oui, **27 membres — désynchronisé** | voir le piège ci-dessous | **ajouter 27, 28, 29, 30 et `Unknown = -1`** |
| Angular `audit.model.ts:39-69` (`AuditActionTypeLabels`) | oui, `Record<AuditActionType, string>` | **erreur de compilation TS** si un membre n'a pas de libellé | **ajouter les 5 libellés** ; exclure `Unknown` du déroulant de filtre |
| Angular `audit-filter.component.ts:67-71` (dropdown) | oui | dérivé des libellés → auto **une fois les libellés ajoutés** | rien |
| Angular affichage (`audit-list:79`, `audit-detail:31`, `audit-timeline:44`, CSV `mss-audit:137`) | oui | `labels[actionType] ?? 'Inconnu'` | rien |
| `client-mobile` | **non** — 0 occurrence d'« audit » | — | **hors périmètre** |

> #### ⚠️ Piège d'ordinaux — le miroir TypeScript est déjà en retard
>
> `client-angular/front/libs/mss/src/core/models/audit.model.ts` se dit « Mirror
> of the C# enum » mais s'arrête à **`BiologyMarkedResolved = 26`** : il lui
> manque **`MailArchiveSent = 27`**, ajouté côté C# par task-223 et réellement
> émis en production.
>
> **Conséquence directe** : appendre naïvement `AttachmentDownload` après
> `BiologyMarkedResolved` lui donnerait la valeur **27** côté TypeScript et
> **28** côté C#. Tout le reste compilerait, le filtre marcherait, et l'écran
> Angular afficherait « Archivage du message envoyé » sur un téléchargement de
> pièce jointe — **un décalage silencieux d'étiquettes sur un journal
> d'imputabilité**.
>
> **Donc** : combler d'abord `MailArchiveSent = 27` (dette de task-223), puis
> ajouter `AttachmentDownload = 28`, `AttachmentsDownloadZip = 29`,
> `AuditPurge = 30` (cf. §5) et le sentinel `Unknown = -1` (cf. §4bis).
> **Écrire les valeurs explicitement** (`= 28`, `= 29`, …), jamais implicitement
> — c'est ce qui rend le décalage impossible plutôt que peu probable. Le sentinel
> est **négatif** précisément pour ne jamais entrer en collision avec un membre
> futur appendu en fin.

**Ordre de déploiement**, imposé par le défaut 4 : `dtos-mss` → `api-mail` →
frontends. À contre-sens, des traces valides remontent étiquetées « Connexion
IMAP ».

**Changement de contrat — minimal et additif.** `MssAuditTraceDto` et
`AuditTraceFilterDto` portent déjà `AuditActionType` typé enum (pas string
libre) : les nouvelles actions sont **filtrables sans toucher au filtre**. Deux
ajouts seulement, tous deux **rétro-compatibles** (System.Text.Json et
TypeScript ignorent un champ inconnu) :

- l'énumération : `AttachmentDownload = 28`, `AttachmentsDownloadZip = 29`,
  `AuditPurge = 30`, `Unknown = -1` ;
- `MssAuditTraceDto.ActionTypeName` (`string`) : le **nom brut** tel que persisté
  en base, toujours renseigné. C'est ce qui rend une action inconnue lisible sans
  mentir sur l'enum (cf. §4bis). `AuditTraceFilterDto` ne change pas.

**Note `client-angular`** : repo **code-only** — la forge écrit le TypeScript et
lance build + tests, mais ne touche jamais à git (branche, commit, push et PR TFS
restent à l'humain).

#### Mise en cohérence des libellés Blazor ↔ Angular (intégré, décision humaine)

`ActionLabels` (Blazor, `Audit.razor:319-337`) s'arrête à `ConnectionError`
(ordinal 15) : **12 actions postérieures n'ont aucun libellé** et s'affichent en
anglais brut. Angular, lui, en libelle **11 sur 12** — il ne lui manque que
`MailArchiveSent`, absent de son enum.

Ce n'est donc pas de la dette cosmétique isolée : **les deux écrans nomment
différemment les mêmes actions**, et un praticien peut consulter l'un ou l'autre.
Un journal d'imputabilité où « Export PDF » s'appelle « MailExportPdf » d'un côté
est diminué au moment précis où il sert. La complétion est un **alignement sur les
libellés Angular existants**, pas une invention de vocabulaire :

| `AuditActionType` | Libellé (source : Angular) | Blazor | Angular |
|---|---|---|---|
| `MailPrint` | Impression | **à ajouter** | existe |
| `MailExportPdf` | Export PDF | **à ajouter** | existe |
| `MailExportEml` | Export EML | **à ajouter** | existe |
| `MailReply` | Réponse | **à ajouter** | existe |
| `MailSuppressionAccept` | Suppression acceptée | **à ajouter** | existe |
| `MailSuppressionRefuse` | Suppression refusée | **à ajouter** | existe |
| `BiologyAcknowledged` | Bio — pris connaissance | **à ajouter** | existe |
| `BiologyPatientCalled` | Bio — rappel patient | **à ajouter** | existe |
| `BiologyPatientSummoned` | Bio — convocation | **à ajouter** | existe |
| `BiologyReferredToColleague` | Bio — adressage confrère | **à ajouter** | existe |
| `BiologyMarkedResolved` | Bio — résolu | **à ajouter** | existe |
| `MailArchiveSent` (27) | Archivage dans Envoyés | **à ajouter** | **à ajouter** |
| `AttachmentDownload` (28) | Téléchargement de pièce jointe | **à ajouter** | **à ajouter** |
| `AttachmentsDownloadZip` (29) | Téléchargement des pièces jointes (ZIP) | **à ajouter** | **à ajouter** |
| `AuditPurge` (30) | Purge du journal d'audit | **à ajouter** | **à ajouter** |
| `Unknown` (−1) | Action inconnue | **à ajouter** | **à ajouter** |

Résultat attendu : **`ActionLabels` (Blazor) et `AuditActionTypeLabels` (Angular)
couvrent les 32 membres, avec des libellés identiques.** Les cinq derniers
libellés sont nouveaux des deux côtés — les écrire une fois, à l'identique.
`Unknown` a un libellé (il doit s'afficher) mais est **exclu des deux déroulants
de filtre** : on ne filtre pas sur un sentinel.

**Testabilité Blazor** : `ActionLabels` est aujourd'hui `private static` **dans la
page `Audit.razor`** — aucun test ne peut l'atteindre. L'extraire dans une classe
statique dédiée (p. ex. `AuditActionLabels`, même assembly), consommée par la page
et par le projet `HealthPlatform.Module.Mss.Plugin.Tests`. Sans cette extraction,
le test de couverture du DOD est impossible à écrire.

Le fallback Blazor `type.ToString()` (`Audit.razor:339-342`) **reste en place** :
c'est le filet pour un membre futur oublié, pas un substitut au libellé.

### 2. Revue de couverture

Passer en revue **l'ensemble** des sorties de données de santé (consultation,
export, impression, envoi, téléchargement, recherche ?) et documenter dans la task
ce qui est tracé et ce qui ne l'est pas **intentionnellement**. Le trou actuel
vient de l'absence d'inventaire.

### 3. Aucune perte silencieuse

Recommandation, par ordre d'importance (à trancher techniquement, mais le point 1
n'est pas négociable) :

1. **`DropOldest` → `Wait`.** Indépendant de toute question de capacité : une
   trace déjà acceptée ne doit jamais être effacée par une trace plus récente.
   C'est ce qui supprime le vecteur d'effacement d'historique.

   > **Correction du 2026-09-07, établie par le test, pas par la revue.** Cette
   > ligne recommandait `DropWrite`. C'était **faux** : dans **tous** les modes
   > `Drop*`, `TryWrite` retourne **`true`** — le canal considère l'écriture
   > acceptée puis écarte un élément par politique, donc l'appelant ne peut pas
   > détecter la saturation. `DropWrite` aurait conservé une perte tout aussi
   > **silencieuse**, en inversant seulement quelle trace disparaît. Seul
   > **`FullMode.Wait`** fait retourner `false` à `TryWrite` quand le canal est
   > plein — et `TryWrite` ne bloque jamais, donc rien n'est ralenti. C'est ce
   > `false` que `AuditService.Enqueue` lit pour dérouter vers le spill.
   > Découvert par `AuditServiceOverflowTests`, qui échouait « spill jamais
   > appelé ».
2. **Observer le retour de `TryWrite`**, avec **deux paliers** — pas trois :
   `TryWrite` → si `false`, **spill immédiat** dans un tampon de secours
   **Redis** (liste par instance ou globale, clé `audit:spill`), rejoué par
   `AuditBackgroundService` dès que le canal a de nouveau de la place → si Redis
   est indisponible aussi, log `Critical` + compteur
   `mss_audit_traces_dropped_total` (avec le type d'action en dimension). La
   perte devient un signal, et n'arrive qu'en dernier recours.

   **Pourquoi pas d'attente bornée (`WriteAsync` ~2 s)** : `IAuditService.Trace`
   est **`void` synchrone** (`IAuditService.cs:15`) et a **13 appelants** — une
   attente asynchrone imposerait soit du sync-over-async, soit une refonte de
   signature sur 13 fichiers pour un gain marginal. Le spill immédiat est
   synchrone-compatible et suffit.

   **Pourquoi Redis et non un fichier local** : `api-mail` tourne en **5
   réplicas** conteneurisés ; un fichier local est **éphémère** (perdu à
   l'éviction du pod) et « rejoué au démarrage » n'est garanti par rien. Il
   porterait de plus des **INS hors base**, sur disque — exactement le défaut
   traité par task-185. Redis est **déjà dans le périmètre HDS** (il cache
   `MailContentDto`, données de santé), partagé entre réplicas, rejouable par
   n'importe lequel. Vérifier que l'instance Redis a la **persistance activée**
   (AOF ou RDB) — sinon le spill ne survit pas à un redémarrage Redis, et il
   faut le dire dans la doc d'exploitation.
3. **Capacité configurable et dimensionnée par la mesure** — exposer
   `mss_audit_channel_depth` et calibrer sur `débit de pointe × temps de drain
   toléré`. `1000` (= 10 lots de `MaxBatchSize`) est arbitraire ; tant que le mode
   reste `DropOldest`, l'augmenter ne fait que retarder l'effacement silencieux.

Aucun palier ne doit **jamais** faire échouer le téléchargement de PJ lui-même :
la dégradation reste interne au chemin d'audit. La **règle d'alerte** sur
`mss_audit_traces_dropped_total > 0` vit dans `devops` (repo hors automation) :
cette task **expose la métrique**, l'humain pose l'alerte.

### 4. Robustesse de la persistance

Le chemin de repli unitaire (`PersistIndividuallyAsync` : un scope et un
aller-retour par trace) est ce qui provoque l'engorgement — vérifier qu'un
ralentissement de base ne peut plus vider le journal.

### 4bis. Ne plus mal étiqueter une action inconnue

Corriger `AuditTraceRepository.cs:246-249` : un `ActionType` non reconnu ne doit
**plus** retomber sur `ImapConnect`. **Décision** — les deux mécanismes sont
nécessaires, aucun ne suffit seul, parce que l'enum part en **ordinal** :

1. **Sentinel `AuditActionType.Unknown = -1`.** Une valeur inconnue en base est
   renvoyée avec cet ordinal, jamais avec celui d'une vraie action. Négatif pour
   ne jamais entrer en collision avec un futur membre appendu ; **jamais écrit en
   base** (valeur de lecture) ; **exclu des déroulants de filtre** des deux
   écrans ; libellé « Action inconnue » des deux côtés.
2. **Champ additif `MssAuditTraceDto.ActionTypeName`** (`string`, toujours
   renseigné avec le nom brut persisté). C'est ce qui rend la valeur d'origine
   **lisible** — « Action inconnue (AttachmentDownload) » — au lieu d'un sentinel
   muet. Sans ce champ, un `Unknown` ne dit pas *quoi* est inconnu.
3. **Logger l'écart** (`Warning`, avec la valeur rencontrée et l'`Id` de la
   trace) : c'est le signal qu'un binaire est en retard sur le contrat.

Les frontends dégradent déjà proprement (`type.ToString()` en Blazor,
`?? 'Inconnu'` en Angular) ; avec 1 + 2 ils affichent une information exacte au
lieu d'une dégradation. Le détail de trace (Blazor et Angular) affiche
`ActionTypeName` quand `ActionType == Unknown`.

### 5. Politique de conservation paramétrable + purge

**Ce que dit la réglementation** (recherche du 2026-09-07 — sources en fin de
task). L'ANS distingue deux natures de traces :

| Nature | Durée | Fondement |
|---|---|---|
| Traces **techniques** (erreurs, évènements système) | 6 mois – 1 an | recommandation CNIL journalisation (2021) : 6 mois à 1 an, extensible « jusqu'à 3 ans et plus » si dûment justifié |
| Traces **applicatives** (accès au dossier patient) | alignées sur le dossier médical, soit **20 ans** | art. R.1112-7 CSP (établissements de santé) |

`MssAuditTrace` est un journal **applicatif** — il porte `PatientIns`,
`PatientName`, `DocumentId` et enregistre qui a lu / exporté / imprimé /
téléchargé un document de santé nominatif. **Une rétention de 365 jours serait
donc sous-dimensionnée** au regard de la doctrine ANS.

Deux nuances déterminantes :

- R.1112-7 vise les **établissements de santé**. Le couloir de ce produit est la
  **médecine de ville**, où aucun texte n'impose 20 ans au praticien libéral : la
  référence usuelle est la prescription en responsabilité médicale (10 ans à
  compter de la consolidation, art. L.1142-28 CSP), l'Ordre recommandant de
  s'aligner sur 20 ans.
- C'est le **responsable de traitement** (praticien / structure) qui fixe la
  durée, **pas l'éditeur**. L'ANS l'énonce explicitement : l'éditeur doit
  **supporter les deux régimes**. D'où le paramétrage, et non une valeur câblée.

**Attendu** — section `Audit:Retention` dans `appsettings.json`, avec deux durées
distinctes (garder 10 ans un `ImapDisconnect` est disproportionné au sens CNIL ;
garder 1 an un `MailExportPdf` est insuffisant au sens ANS) :

```jsonc
// appsettings.json — surcharge explicite. Les mêmes valeurs sont les DÉFAUTS
// de la classe d'options : retirer cette section ne désactive rien, elle
// applique ces durées (cf. contraintes ci-dessous).
"Audit": {
  "Retention": {
    // Durées : absente ⇒ défaut ci-dessous ; 0 explicite ⇒ purge de cette
    // famille désactivée (legal hold). int? obligatoire — cf. contraintes.
    "HealthDataAccessDays": 3653,  // 10 ans — accès et sorties de données de santé
    "TechnicalDays": 365,          // 1 an — ImapConnect/Disconnect, Smtp*, ConnectionError
    // Fréquence minimale d'une passe de purge PAR TENANT (TimeSpan, pas cron —
    // il n'y a aucune bibliothèque cron dans api-mail). Défaut 24 h.
    "PurgeInterval": "1.00:00:00"
  }
}
```

**Déclenchement — ni cron, ni énumération des bases.** Le repo n'a **aucun
planificateur** (ni Quartz, ni Hangfire, ni NCrontab) et, plus déterminant,
**aucun moyen d'énumérer les bases praticien** : tout est scopé par
`UserContextInfo`, et la seule requête sur `pg_database` (`MigrationHelper.cs:72`)
teste l'existence d'une base par son nom. Un `BackgroundService` global n'aurait
**rien à parcourir**. Le seul composant qui détient légitimement le contexte de
chaque tenant est `AuditBackgroundService`, qui ouvre déjà un scope par groupe de
traces avec la connexion du tenant (`PersistBatchAsync`). D'où le design :

- la purge est **opportuniste, par tenant** : au moment de persister un lot pour
  un tenant, si sa dernière passe date de plus de `PurgeInterval` (marqueur Redis
  `audit:purge:{tenant}:last`, TTL = intervalle), lancer la purge de **ce**
  tenant dans le même scope, **après** la persistance du lot ;
- un tenant qui ne produit aucune trace n'est pas purgé — c'est acceptable : sa
  table ne grossit pas non plus, et il sera purgé à sa prochaine activité ;
- la passe est **bornée** (lots de N lignes, N configurable, défaut 5 000) et
  **non bloquante** pour le drain du canal : si elle échoue, on la logue et on
  la retentera à la prochaine occasion — jamais au prix de traces en attente.

Ce design fait aussi tomber la nécessité d'une valeur `PurgeSchedule` cron — d'où
`PurgeInterval`.

**La purge se trace elle-même — provision explicite.** Nouveau membre
`AuditActionType.AuditPurge = 30`, une trace par passe et par tenant, avec la
borne appliquée, le nombre de lignes supprimées et la famille (`ServerRequest`
peut porter le résumé sérialisé). Deux contraintes qui ne sautent pas aux yeux :

- **`UserId` = l'email du tenant**, pas `"system"`. `GetTracesAsync` filtre
  `t.UserId == UserContextInfo.Email` (`AuditTraceRepository.cs:91`) : une trace
  portant un autre `UserId` serait **invisible dans les deux écrans**. L'acteur
  système se marque ailleurs — `UserSessionId = "system:audit-purge"`,
  `SourceIp`/`UserAgent` nuls.
- **Famille « données de santé »** pour `AuditPurge` : cette trace prouve *ce qui
  a été supprimé et quand* — elle doit survivre aussi longtemps que ce qu'elle
  documente, pas comme une trace technique.

Classement des `AuditActionType` en deux familles, à figer dans le code (et non
par convention de nommage), avec **valeur par défaut = famille « données de
santé »** pour tout membre non classé — un oubli de classement doit conserver
plus longtemps, jamais moins.

Contraintes d'implémentation, toutes vérifiables :

- **Configuration absente ⇒ repli sur les durées par défaut** (3653 j / 365 j),
  portées par la **classe d'options elle-même** — pas par le JSON, pas par un
  `??` disséminé dans le service de purge. Une installation qui ne configure rien
  a donc une politique de conservation conforme, et non pas *aucune* politique :
  c'est précisément le défaut 3 qu'on ferme, il ne doit pas se rouvrir par un
  oubli de déploiement. Le repli est **journalisé au démarrage** (`Warning`),
  avec la valeur appliquée, pour qu'il ne soit jamais silencieux.
- **Valeur invalide** (négative, non numérique, absurdement basse) ⇒ **même
  repli** sur le défaut + `Warning`. Jamais d'interprétation permissive : une
  saisie erronée ne doit pouvoir ni supprimer plus, ni conserver moins que le
  défaut.
- **`0` explicite = purge désactivée** — et **seulement** `0` explicite. C'est
  l'échappatoire *legal hold* : en cas de contentieux, les délais R.1112-7 sont
  suspendus, l'exploitant fige le journal sans changer de version. À distinguer
  strictement de l'absence de clé, qui retombe sur le défaut. Un `int?` (ou
  équivalent) est donc nécessaire : un `int` non nullable rend les deux cas
  indiscernables.
- **Index sur `Timestamp`** — sans lui la purge scanne la table entière, sur
  chaque base praticien.
- **La purge est la seule suppression autorisée** (PGSSI-S : les traces ne
  doivent pas pouvoir être modifiées pendant leur conservation) et **elle se trace
  elle-même** : borne appliquée, nombre de lignes supprimées, base concernée.
- **Purge par lot**, pour ne pas reproduire l'engorgement qu'on corrige au
  défaut 2 — tenant par tenant, selon le déclenchement opportuniste décrit
  ci-dessus (jamais un balayage global : il n'existe rien à balayer).
- **Volumétrie à mesurer, pas à supposer** : `MailReceive` est tracé **par
  message synchronisé** (`ImapService.cs:1864`) et relève de la famille « données
  de santé » — dix ans de cette famille, c'est l'essentiel du poids de la table.
  Consigner dans la task un ordre de grandeur (lignes/an pour une boîte
  représentative) ; le partitionnement par date est **hors scope** mais doit
  être nommé comme suite probable si l'ordre de grandeur l'exige.
- **Suspension en cas de contentieux** — les délais R.1112-7 sont suspendus par
  tout recours. Le mécanisme est le `0` explicite décrit plus haut ; à documenter
  comme tel dans la doc d'exploitation, avec la contrepartie (croissance non
  bornée de la table tant que la suspension dure).

### 6. Deux régimes de contenu, à ne pas confondre

- **Journal d'audit (base)** : identifiant patient **attendu**, contenu clinique
  **interdit** — pas de corps de message, pas de contenu de document, pas de
  résultat de biologie. On trace *qu'un document a été sorti pour tel patient*,
  jamais *ce que le document disait*.
- **Logs Serilog / Seq / OTLP** : ni INS, ni traits patient, ni contenu — règle
  task-184, inchangée et non affaiblie par cette task.

Le chemin de téléchargement de PJ est l'endroit où les deux régimes se croisent :
c'est là que le test doit le prouver. Voir l'arbitrage tranché ci-dessous.

---

> ### ⚖️ Arbitrage tranché (humain, 2026-09-07) — l'audit porte l'INS, les logs jamais
>
> **Le journal d'audit persisté en base identifie le patient. Les logs
> d'exploitation (Seq, Graylog, OTLP) ne le font jamais.** Ce sont deux
> traitements distincts, et les confondre est ce qui rendait le DOD initial
> contradictoire.
>
> | | Logs Seq / Graylog / OTLP | Journal d'audit (`MssAuditTrace`, base praticien) |
> |---|---|---|
> | Finalité | exploitation, débogage | **imputabilité, preuve** |
> | Population lisible | ops, éditeur, support, prestataires | restreinte, elle-même tracée |
> | Hébergement | pas nécessairement HDS | HDS, base du praticien |
> | Conservation | 6 mois – 1 an | 10 – 20 ans (cf. §5) |
> | **INS / traits patient** | **jamais** → task-184 | **oui — c'est l'objet même** |
>
> **Motif** : un journal d'accès qui ne dit pas *à quel patient* se rapportait le
> document répond à « quelqu'un a téléchargé quelque chose », pas à « qui a accédé
> au dossier de M. X ». Or c'est exactement la question posée en litige, en
> réclamation patient ou en contrôle CNIL. Sans l'INS, la trace est ininterprétable
> au moment où elle sert.
>
> **Conséquences, toutes appliquées dans cette task :**
>
> - `PatientIns` / `PatientName`, déjà persistés par `BiologyAckService.cs:183`,
>   `EmailBuildingService.cs:116` et `CdaParsingService.cs:219`, et relus par
>   `AuditTraceRepository.cs:140` (recherche par INS), **restent** — comportement
>   voulu, pas dette. Aucune migration, aucune task de suite.
> - Les **nouvelles** traces `Attachment*` **renseignent** le contexte patient
>   (`PatientIns`, `DocumentId`, `DocumentCategory`) **quand il est disponible** —
>   c'est-à-dire quand la PJ se résout à un document médical connu de la base. Sur
>   le chemin de repli IMAP, où ce contexte n'existe pas, la trace est émise
>   quand même avec ce qu'elle a : **une trace sans INS vaut mieux qu'aucune
>   trace**, et l'absence de contexte ne doit jamais bloquer la journalisation.
> - La frontière est ce qui doit être **testé** : les mêmes champs qui sont exigés
>   dans la trace persistée doivent être absents des logs Serilog émis par le même
>   chemin de code. C'est le seul endroit du repo où les deux régimes se croisent.
> - La section conformité de cette task, qui affirmait « INS : ne doit **pas**
>   figurer en clair dans les traces », était une erreur de rédaction du gabarit
>   PO — elle décrivait la règle *logs* appliquée au mauvais objet. Corrigée.

---

### Hors scope

- L'assainissement des logs applicatifs Serilog / OTLP → task-184 (mergée). Cette
  task ne fait que **vérifier la non-régression** sur le chemin qu'elle touche.
- La **refonte du stockage** du journal d'audit (déplacement vers un magasin
  dédié, WORM, signature des traces). Seules la durée de conservation et la purge
  entrent dans cette task.
- Le retrait de l'INS du journal d'audit — **écarté par arbitrage** (2026-09-07),
  ce n'est pas une dette à traiter plus tard : c'est le comportement voulu.
- `client-mobile` — aucun écran d'audit (0 occurrence d'« audit » dans `src/`).
- Le **partitionnement** de `MssAuditTrace` par date et toute optimisation de
  stockage au-delà de l'index `Timestamp` — à ouvrir si l'ordre de grandeur
  consigné au §5 l'exige.
- La **règle d'alerte** sur `mss_audit_traces_dropped_total` → `devops` (humain).
- La **persistance Redis** (AOF/RDB) — configuration d'infrastructure ; la task
  la vérifie et la documente, ne la modifie pas.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] `AuditActionType` (C#) : `AttachmentDownload = 28`,
      `AttachmentsDownloadZip = 29`, `AuditPurge = 30` **appendus en fin
      d'énumération**, plus le sentinel `Unknown = -1` (aucune valeur ordinale
      existante déplacée — vérifié par un test qui fige les ordinaux des 28
      membres antérieurs et des 4 nouveaux)
- [ ] `MssAuditTraceDto.ActionTypeName` (`string`) ajouté, toujours renseigné ;
      `AuditTraceFilterDto` inchangé
- [ ] `dtos-mss` republié (`/publish-dtos`, bump depuis 285.0.0) et les
      `PackageReference` consommateurs mis à jour
- [ ] **Angular** `audit.model.ts` : `MailArchiveSent = 27` (dette task-223),
      `AttachmentDownload = 28`, `AttachmentsDownloadZip = 29`, `AuditPurge = 30`,
      `Unknown = -1` — **valeurs écrites explicitement**, jamais implicites ;
      `AuditTraceDto.actionTypeName` ajouté
- [ ] **Test Angular figeant les ordinaux TS** (`audit.model.spec.ts`) : chaque
      membre est asserté contre sa valeur numérique attendue, table identique à
      celle du test C#. Un test TS ne peut pas lire le C# : ce sont **deux tests
      jumeaux contre la même table**, pas un test croisé. Il n'existe **aucun**
      `.spec.ts` sous `features/audit/` ni pour `audit.model.ts` : c'est ce vide
      qui a laissé passer la désynchronisation de task-223
- [ ] **Angular** `AuditActionTypeLabels` : les 5 libellés FR ajoutés
      (`MailArchiveSent`, `AttachmentDownload`, `AttachmentsDownloadZip`,
      `AuditPurge`, `Unknown`) — le type `Record<AuditActionType, string>` fait
      échouer le build sinon ; `Unknown` **exclu** du déroulant de filtre
      (`audit-filter.component.ts:67-71`) ; le détail affiche `actionTypeName`
      quand `actionType === Unknown`
- [ ] **Blazor** : `ActionLabels` **extrait** de `Audit.razor` vers une classe
      statique testable (même assembly) et complété de **16 à 32 entrées** — les 12
      libellés antérieurs manquants repris **à l'identique** d'Angular, plus les 5
      nouveaux ; `Unknown` **exclu** du déroulant (`Audit.razor:51-60`) ; le détail
      affiche `ActionTypeName` quand `ActionType == Unknown`
- [ ] **Test de couverture des libellés** côté Blazor
      (`HealthPlatform.Module.Mss.Plugin.Tests`) : chaque membre de
      `AuditActionType` a une entrée — un membre futur non libellé fait échouer le
      test. C'est l'équivalent du garde-fou que le type `Record<>` procure déjà
      gratuitement à Angular ; sans lui, la complétion d'aujourd'hui redevient
      incomplète au prochain membre ajouté
- [ ] **Libellés identiques** entre Blazor et Angular sur les 32 membres — vérifié
      explicitement, les deux écrans nommant les mêmes actions pour le même
      praticien
- [ ] Build + tests verts sur `client-angular` (code-only : aucune opération git)
      et sur `client-blazor`
- [ ] Un `ActionType` inconnu **n'est plus** étiqueté `ImapConnect` : test unitaire
      sur le remplaçant de `AuditTraceRepository.ParseActionType` — renvoie
      `Unknown`, `ActionTypeName` porte le nom brut, un `Warning` est émis avec
      l'`Id` de la trace
- [ ] `Unknown` n'est **jamais** persisté : test unitaire sur `AuditService.Trace`
      (refus ou remplacement, au choix — mais jamais la chaîne `"Unknown"` en base)
- [ ] Test d'intégration : le téléchargement d'une PJ produit une trace d'audit
      (ce test doit échouer sur le code actuel — le vérifier explicitement)
- [ ] Test d'intégration : l'export ZIP de toutes les PJ produit **une** trace,
      `AttachmentCount` = nombre de PJ empaquetées
- [ ] Test unitaire : la trace est émise **après** résolution réussie et **avant**
      `return File(...)`, `Success = true` ; **aucune** trace quand la résolution
      échoue (404) — symétrie stricte avec `MailExportController.TraceMailAction`
- [ ] Test unitaire : la trace de téléchargement identifie l'acteur, l'action, la
      ressource et l'horodatage, et **renseigne le contexte patient**
      (`PatientIns`, `DocumentId`) quand la PJ se résout à un document médical connu
- [ ] Test unitaire : quand le contexte patient est **absent** (chemin de repli
      IMAP), la trace est **quand même émise** — l'absence d'INS ne bloque jamais
      la journalisation
- [ ] Test unitaire : la trace ne contient **aucun contenu clinique** — ni corps de
      message, ni contenu de document, ni résultat
- [ ] Test : sur le **même** chemin de code, les logs Serilog émis ne contiennent
      ni INS ni traits patient (non-régression task-184 — c'est la frontière entre
      les deux régimes qui est vérifiée, pas seulement chacun de son côté)
- [ ] `FullMode` du canal d'audit est `Wait` (ni `DropOldest`, ni `DropWrite` — dans tous les modes `Drop*`, `TryWrite` rend `true` et la perte reste silencieuse) — test unitaire :
      une trace déjà mise en file n'est jamais évincée par une trace plus récente
- [ ] Test unitaire : quand la file d'audit est saturée, la trace part dans le
      **spill Redis** et est **rejouée** par `AuditBackgroundService` dès que le
      canal a de la place — aucune perte, ordre préservé au mieux
- [ ] Test unitaire : file saturée **et** Redis indisponible ⇒ log `Critical` +
      incrément de `mss_audit_traces_dropped_total` (dimension : type d'action) —
      la perte est un signal, jamais un silence. La **règle d'alerte** sur cette
      métrique relève de `devops` (hors automation) : la task expose la métrique,
      elle ne pose pas l'alerte
- [ ] `IAuditService.Trace` reste **`void` synchrone** — aucun sync-over-async,
      aucune refonte des 13 appelants
- [ ] Test unitaire : la saturation du canal ne fait pas échouer la requête HTTP
      de téléchargement (la dégradation reste interne au chemin d'audit)
- [ ] Test unitaire : un ralentissement de la persistance ne provoque pas de perte
      de trace (simulation du chemin de repli unitaire `PersistIndividuallyAsync`)
- [ ] Section `Audit:Retention` présente dans `appsettings.json`, liée à une
      classe d'options typée, avec les deux durées documentées
- [ ] Test unitaire : section `Audit:Retention` **absente** ⇒ les durées par défaut
      (3653 j / 365 j) s'appliquent, portées par la classe d'options, et un
      `Warning` de démarrage nomme la valeur appliquée
- [ ] Test unitaire : valeur **invalide** (négative, non numérique) ⇒ même repli
      sur le défaut + `Warning` — jamais d'interprétation permissive
- [ ] Test unitaire : `0` **explicite** sur une famille ⇒ purge **de cette
      famille** désactivée (legal hold), l'autre famille continuant d'être purgée ;
      ce cas est distinct de l'absence de clé (type nullable, les deux ne se
      confondent pas)
- [ ] Test unitaire : **déclenchement opportuniste** — la purge d'un tenant
      s'exécute depuis `AuditBackgroundService` après la persistance d'un lot, au
      plus une fois par `PurgeInterval` (marqueur Redis `audit:purge:{tenant}:last`)
      ; deux lots dans l'intervalle ⇒ une seule passe
- [ ] Test unitaire : une passe de purge qui échoue **ne bloque pas** le drain du
      canal et **n'empêche pas** la persistance des traces en attente
- [ ] Aucun `BackgroundService` de purge **global** n'est introduit (il n'existe
      aucune énumération des bases praticien à parcourir)
- [ ] Test unitaire : la purge respecte les deux familles de durées (une trace
      technique au-delà de `TechnicalDays` est purgée ; une trace d'accès aux
      données de santé du même âge ne l'est pas)
- [ ] Test unitaire : un `AuditActionType` non classé est traité comme « données
      de santé » (conservation la plus longue par défaut)
- [ ] Migration : index sur `MssAuditTrace.Timestamp` (audit de migration règle 7c)
- [ ] La purge écrit elle-même une trace `AuditPurge` par passe et par tenant
      (borne, nombre de lignes, famille), **`UserId` = email du tenant** (sinon
      invisible dans les écrans — filtre `AuditTraceRepository.cs:91`),
      `UserSessionId = "system:audit-purge"` ; test d'intégration : la trace
      `AuditPurge` **apparaît** dans `GET api/v1/Audit/traces` du tenant
- [ ] `AuditPurge` classé famille « données de santé » (test : non purgé au délai
      technique)
- [ ] Inventaire de couverture documenté dans la task : sorties de données de santé
      tracées / non tracées, avec justification pour chaque exclusion
- [ ] Non-régression : les traces existantes (lecture, export PDF/EML, impression,
      envoi) restent produites à l'identique
- [ ] Aucun **contenu clinique** dans les traces d'audit, et **aucune donnée
      identifiante** (INS, traits) dans les logs Serilog / OTLP. L'INS **dans le
      journal d'audit** est voulu et n'est pas un manquement (arbitrage 2026-09-07)

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
   (l'AppHost **ne lance pas** les frontends). Puis :
   - **Blazor** : `cd Client/Blazor && dotnet run --project Src/Shell` — ouvrir
     l'URL affichée (`launchSettings.json` : `http://localhost:5295`) ;
   - **Angular** : `cd Client/Angular/front && npx nx serve mss` — l'app `mss`
     (pas `weda2`, cible du `npm start`).
   Pré-requis : le paquet `dtos-mss` republié est **déjà** consommé par le
   backend lancé (ordre `dtos-mss` → `api-mail` → fronts) — sinon l'étape 4quater
   se produit sur les vraies traces.
2. Ouvrir un message porteur de pièces jointes (données anonymisées) et télécharger
   une PJ, puis « Télécharger tout ».
3. Consulter le journal d'audit (écran « Journal d'audit » Blazor, ou la table
   `MssAuditTrace` de la base du praticien) :
   **attendu** — une trace `AttachmentDownload` et une trace
   `AttachmentsDownloadZip`, avec acteur, action, ressource, horodatage, et
   `AttachmentCount` sur la seconde. Avant correctif : **aucune** trace, alors
   qu'un export PDF du même message en produit une.
   Puis tenter le téléchargement d'une PJ **inexistante** (URL modifiée) :
   **attendu** — 404 et **aucune** trace, comme pour un export qui échoue.
4. Comparer : exporter le même message en PDF → la trace existante est bien là. Les
   deux familles d'action sont désormais symétriques.
4bis. **Écran « Journal d'audit » — Blazor** (`/audit`) :
   - la ligne du téléchargement s'affiche avec un **libellé français** (pas
     « AttachmentDownload » en brut) ;
   - **dérouler la liste complète des types d'action** : plus **aucun** libellé en
     anglais brut (avant correctif : `MailPrint`, `MailExportPdf`, `MailExportEml`,
     `MailReply`, `MailSuppression*`, `Biology*`, `MailArchiveSent` s'affichent
     ainsi) ;
   - ouvrir l'écran Angular côte à côte et comparer : **mêmes libellés des deux
     côtés** pour les mêmes actions ;
   - le déroulant « Type d'action » propose les entrées « Téléchargement de pièce
     jointe », « Téléchargement des pièces jointes (ZIP) » et « Purge du journal
     d'audit », mais **pas** « Action inconnue » ; filtrer sur un téléchargement
     ne renvoie **que** les téléchargements ;
   - l'export CSV porte le même libellé.
4ter. **Écran d'audit — Angular** (`libs/mss`, route `audit`) :
   - mêmes vérifications (liste, détail, timeline, filtre, export CSV) ;
   - **contrôle du décalage d'ordinaux** — c'est le point le plus important de ce
     plan : vérifier qu'un téléchargement de PJ n'affiche **pas** « Archivage du
     message envoyé », et qu'un envoi archivé n'affiche pas « Téléchargement de
     pièce jointe ». Croiser au moins trois actions différentes avec la table
     d'audit en base. Un décalage d'un cran est invisible sur un seul cas.
4quater. **Étiquette inconnue** : insérer à la main en base une trace
   `ActionType = 'ActionQuiNExistePas'` (avec le `UserId` du praticien connecté),
   rafraîchir les deux écrans.
   **Attendu** : la ligne s'affiche « Action inconnue », le détail montre
   `ActionQuiNExistePas` (champ `ActionTypeName`), et un `Warning` serveur la
   mentionne avec son `Id`. Le déroulant de filtre ne propose **pas** « Action
   inconnue ». Avant correctif : elle s'affiche « Connexion IMAP », sans aucun
   signal.
5. **Contre-pression** : arrêter le conteneur PostgreSQL (`docker stop`), générer
   un volume de traces important (synchronisation d'une boîte fournie), puis
   redémarrer la base.
   **Attendu** : pendant l'arrêt, `mss_audit_channel_depth` monte puis le spill
   Redis se remplit (clé `audit:spill`, visible avec `redis-cli LLEN`) ; après
   redémarrage de la base, le spill se vide et **toutes** les traces sont en base,
   `mss_audit_traces_dropped_total` reste à **0**. Avant correctif : les traces
   au-delà des 1000 premières disparaissent sans aucun signal.
   Variante : arrêter **aussi** Redis pendant la saturation → **attendu** — log
   `Critical` et `mss_audit_traces_dropped_total` incrémenté du nombre exact de
   traces perdues, avec le type d'action en dimension.
6. **Non-effacement de l'historique** : noter la trace la plus ancienne visible,
   rejouer l'étape 5, vérifier qu'elle est **toujours là**. Avant correctif
   (`DropOldest`), elle disparaît au profit des traces récentes.
7. **Rétention** : régler `Audit:Retention:TechnicalDays` à `1` et
   `PurgeInterval` à `00:00:10`, insérer en base une trace technique (connexion
   IMAP) et une trace `MailRead` toutes deux datées de 48 h, puis **provoquer une
   activité** du praticien (ouvrir un message) — c'est ce qui déclenche la passe
   opportuniste, il n'y a pas de bouton ni de cron.
   **Attendu** : la trace technique est purgée, la trace `MailRead` du même âge
   est **conservée**, et une trace `AuditPurge` **visible dans l'écran** porte le
   nombre de lignes supprimées. Rouvrir un message dans les 10 s : **aucune**
   seconde passe.
8. **Repli de configuration** : retirer la section `Audit:Retention`, relancer.
   **Attendu** : un `Warning` de démarrage annonce les durées par défaut
   appliquées (3653 j / 365 j), et la purge tourne sur ces valeurs — pas
   d'installation sans politique de conservation.
   Puis poser `TechnicalDays: 0` explicitement et relancer : **attendu** — la
   purge des traces techniques est désactivée (legal hold), avec un log qui le
   dit. Les deux situations doivent se distinguer dans les logs.
9. **Frontière des deux régimes**, sur le même téléchargement :
   - dans la **table d'audit** — la trace porte bien `PatientIns` et `DocumentId`
     quand la PJ est un document médical connu ; elle ne porte **aucun** contenu
     clinique (corps de message, contenu de document, résultat) ;
   - dans **Seq** — la même requête n'a laissé **ni INS ni traits patient**
     (non-régression task-184) ;
   - sur une PJ **sans** contexte patient (chemin IMAP), la trace existe quand
     même, avec un contexte patient vide.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : correctif de conformité PGSSI-S § journalisation —
  imputabilité des accès et des sorties de données de santé ; RGPD art. 5.1.e
  (limitation de la conservation) pour la politique de rétention
- **INS** : **deux régimes distincts, tranchés le 2026-09-07.** Dans le **journal
  d'audit persisté** (base praticien, HDS, accès restreint, conservation longue),
  l'INS **doit** figurer — il identifie le patient dont le dossier a été accédé,
  ce qui est la finalité même de l'imputabilité et la seule façon d'exploiter la
  trace en litige. Dans les **logs d'exploitation** (Seq, Graylog, export OTLP),
  il ne doit **jamais** figurer — règle task-184, inchangée. Les nouvelles traces
  `Attachment*` renseignent donc `PatientIns` / `DocumentId` quand le contexte est
  disponible, et sont émises sans lui quand il ne l'est pas.
- **Authentification PS** : inchangée — l'acteur tracé est l'identité PS
  authentifiée (PSC / e-CPS). **La task ne touche ni l'authentification ni
  l'autorisation** : le défaut porte sur l'imputabilité seule.
- **Habilitations** : inchangées ; l'accès au journal d'audit doit rester restreint
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : **cœur du sujet**. Évènements à couvrir : téléchargement de
  pièce jointe (unitaire et archive), en plus des consultations, exports,
  impressions et envois déjà tracés. Immuabilité des traces pendant toute la durée
  de conservation — la purge est la seule suppression admise, et elle se trace.
- **Durée de conservation** : **fixée par cette task, paramétrable** — deux
  familles (traces applicatives d'accès aux données de santé / traces techniques).
  Défauts proposés : 3653 j (10 ans) et 365 j (1 an), réglables à la hausse
  jusqu'à 20 ans sans changement de code. La durée retenue relève du
  **responsable de traitement**, pas de l'éditeur ; le produit doit supporter les
  deux régimes.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : **à mettre à jour** — l'absence de trace sur les
  téléchargements de pièces jointes empêche de reconstituer les accès en cas
  d'enquête (CNIL ou interne). Signaler au DPO que **les périodes antérieures ne
  sont pas reconstituables** sur ces deux routes, et que le journal a pu perdre
  des traces sous charge sans que rien ne l'indique. Documenter la durée de
  conservation retenue dans le registre des traitements.

### Sources réglementaires (consultées le 2026-09-07)

- ANS — [Quelle est la durée de conservation des traces techniques et applicatives des dossiers patient ?](https://esante.gouv.fr/faq/quelles-est-la-duree-de-conservation-des-traces-techniques-et-applicatives-des-dossiers-patient) — distingue traces techniques (6 mois–1 an) et traces applicatives (alignées sur le dossier médical, 20 ans)
- Légifrance — [Article R.1112-7 CSP](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000036658351) — 20 ans à compter du dernier séjour ou de la dernière consultation externe ; délais suspendus par tout recours
- CNIL — [Recommandation relative aux mesures de journalisation](https://www.cnil.fr/sites/cnil/files/atoms/files/recommandation_-_journalisation.pdf) — 6 mois à 1 an en principe, extensible si dûment justifié
- ANS — [Référentiel d'imputabilité PGSSI-S](https://esante.gouv.fr/sites/default/files/media_entity/documents/pgssi_referentiel_imputabilite_v1.0_0.pdf)
- ANS — [Référentiel socle MSSanté #2 — Clients de messageries](https://esante.gouv.fr/sites/default/files/media/document/ans_mss_ref2_clients_de_messageries_mssante_v1.0.1_20240118.pdf)

## Branches

Créées par `/start` le 2026-09-07 depuis `origin/develop`.
Nom unique sur les trois repos pushables : `fix/task-186-journal-audit-incomplet-et-non-borne`.

- `api-mail` (pushed) : `fix/task-186-journal-audit-incomplet-et-non-borne` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-186-journal-audit-incomplet-et-non-borne
- `dtos-mss` (pushed) : `fix/task-186-journal-audit-incomplet-et-non-borne` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-186-journal-audit-incomplet-et-non-borne
- `client-blazor` (pushed) : `fix/task-186-journal-audit-incomplet-et-non-borne` — https://github.com/codengine-technologies/HealthPlatform.Client/tree/fix/task-186-journal-audit-incomplet-et-non-borne
- `client-angular` (code-only) : aucune branche créée. La forge écrit le TypeScript sur la branche actuellement checked out dans `Client/Angular/` — **snapshot au `/start` : `feature/nova-rewriting-mss`**. L'humain gère branche, commit, push et PR TFS.

Préfixe `fix/` : la task corrige quatre défauts de conformité constatés, elle
n'ajoute pas une capacité produit. Cohérent avec `fix/task-187-*` et
`fix/task-291-*`.

**Ordre de travail imposé** (cf. §1bis « Ordre de déploiement ») :
`dtos-mss` → `api-mail` → `client-blazor` / `client-angular`. Le contrat
`AuditActionType` doit être publié avant que le backend écrive les nouvelles
traces, sinon le défaut 4 se déclenche sur des traces valides.

## Timings

*(généré par `tools/timing/report.sh --task task-186 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 1 min 33 s | — | — | — | — |
| /develop | ok | 50 min 08 s | 11 (5 min 17 s) | 15 (10 min 04 s) | — | dtos-mss 1B/0T, api-mail 5B/10T, client-angular 2B/4T, client-blazor 3B/1T |
| /sonar | ok | 21 min 37 s | 3 (45 s) | 12 (10 min 10 s) | 2 (3 min 52 s) | 1 itération(s), api-mail 3B/12T |
| /lint-angular | ok | 6 min 57 s | 1 (1 min 12 s) | 1 (1 min 06 s) | — | 1 itération(s), client-angular 1B/1T |
| /lint-mobile | skipped | 13 s | — | — | — | client-mobile non listé dans Repos et arbre de travail vide |
| /verify-visual | skipped | 15 s | — | — | — | aucun écran client-mobile touché ; les écrans d'audit sont Blazor/Angular, hors périmètre v1 |
| /review | ok | 9 min 44 s | 3 (1 min 02 s) | 2 (1 min 41 s) | — | dtos-mss 1B/0T, client-blazor 1B/1T, api-mail 1B/1T |
| /tech-writer | ok | 6 min 46 s | — | — | — | — |
| **Total cycle** | | **1 h 37 min** | **18 (8 min 19 s)** | **30 (23 min 01 s)** | **2 (3 min 52 s)** | |

Autres commandes mesurées : lint ×3 (1 min 47 s), nuget-wait ×1 (1.0 s)

## Develop log — 2026-09-07

### Ce qui est livré

| Défaut | État | Où |
|---|---|---|
| 1 — sorties de PJ non tracées | **fait** | `MailController.TraceAttachmentRelease` + les deux routes |
| 2 — perte silencieuse / effacement d'historique | **fait** | `FullMode.Wait`, `AuditService.Enqueue`, spill Redis + rejeu, 4 métriques |
| 3 — aucune conservation | **fait** | `AuditOptions`, `AuditRetentionPolicy`, purge opportuniste par tenant, trace `AuditPurge` |
| 4 — action inconnue mal étiquetée | **fait** | sentinel `Unknown = -1`, `ActionTypeName`, `Enum.IsDefined`, `Warning` |
| Frontends | **fait** | Angular : enum +5, libellés +5, `Unknown` hors filtre, nom brut affiché. Blazor : libellés 16 → 32, extraits et testés |

**Contrat** : `dtos-mss` republié en **454.0.0** (CI run #454 verte), consommateurs bumpés.

### Deux corrections de la spec, établies par le code et par les tests

1. **`DropWrite` était un faux correctif.** La task recommandait
   `DropOldest → DropWrite`. Dans **tous** les modes `Drop*`, `TryWrite` retourne
   **`true`** : le canal considère l'écriture acceptée puis écarte un élément par
   politique, donc l'appelant ne peut pas détecter la saturation. `DropWrite`
   aurait conservé une perte tout aussi silencieuse, en inversant seulement
   quelle trace disparaît. Le mode retenu est **`Wait`** — `TryWrite` n'y bloque
   jamais et rend `false` quand le canal est plein. Découvert par
   `AuditServiceOverflowTests`, pas par la revue.
2. **Aucune migration n'était nécessaire.** L'index `IX_MssAuditTraces_Timestamp`
   existe déjà (`MailDataContext.cs:500`, créé par `20240101_SetupMigration`).

### Écarts au DOD — assumés et nommés

- **Contexte patient absent des traces `Attachment*`.** Ni `AttachmentDto` ni
  `AttachmentStreamResult` ne portent `DocumentId` ou l'INS. Les renseigner
  imposerait soit une requête supplémentaire sur un chemin dont la latence est
  délibérément instrumentée (task-252), soit l'élargissement d'un DTO de contrat
  et un second cycle NuGet. Le principe de la task s'applique : *une trace sans
  INS vaut mieux qu'aucune trace*, et l'absence de contexte ne doit jamais
  bloquer la journalisation. **Enrichissement = suite à décider** (il faut
  trancher la voie de streaming).
- **Tests non écrits** : purge au niveau repository (nécessite un contexte base
  par tenant), rejeu du spill de bout en bout, frontière Serilog sur le même
  chemin de code, test d'intégration ZIP. Les comportements sont couverts au
  niveau unitaire (`AuditRetentionPolicyTests`, `AuditServiceOverflowTests`),
  pas au niveau intégration.
- **Alerte sur `mss_audit_traces_dropped_total`** : hors périmètre (`devops`).
  La métrique est exposée, la règle reste à poser par l'humain.
- **Persistance Redis (AOF/RDB)** : non vérifiée. Sans elle le spill ne survit
  pas à un redémarrage Redis — exigence d'exploitation à confirmer.

### Rouges pré-existants, non imputables à cette task

- `ImapServiceTests.GetFolderTodayAsync_HappyPath_TagsTheImapActivityWithPerCommandDurations`
  — `TypeInitializationException` sur `ActivitySources`. **Vérifié rouge à
  l'identique sur `origin/develop`** (worktree dédié), donc antérieur.
- `client-angular` : le build **production** échoue car
  `apps/mss/src/environments/environment.prod.ts` n'est **ni suivi par git ni
  présent** sur la branche `feature/nova-rewriting-mss`. Sans rapport avec
  task-186. Le build **développement** et les tests (`mss-lib`, 334 tests)
  passent.
- Contexte : la suite api-mail est non déterministe sur trois assemblies
  (task-291, parquée sur fail-fast).

### Écarts de pré-flight relevés

- **Deux `wip-*` coexistent** (`task-186`, `task-291`). Le playbook demande
  d'abandonner ; j'ai poursuivi parce que task-291 est **parquée sur un
  fail-fast documenté**, état que le protocole `/forge` produit lui-même
  (« laisse la task dans son état actuel »). Appliquer la règle à la lettre
  gèlerait toute la forge tant que task-291 n'est pas arbitrée.
- `client-angular` avait deux fichiers modifiés (`environment.ts` × 2) — WIP
  humain sur un repo code-only, préservé, non touché.

### Passe qualité §Q

`api-mail` et `client-blazor` : relecture du diff sur les axes réutilisation /
simplification / efficacité — **aucun cleanup appliqué**, donc pas de commit
vide ni de re-validation (le seul point relevé, deux allers-retours Redis dans
`TrySpillAsync`, n'est emprunté que sous saturation et garde la file bornée).
`dtos-mss` : exclu (porteur de contrat). `client-angular` : code-only, aucune
opération git.

### Timings

Mesurés par `Tools/timing` — voir `metrics/timings.jsonl` et la section
`## Timings` régénérée par `step.sh end`.


## Sonar log — 2026-09-07

Infrastructure : conteneurs arrêtés depuis 4 jours, redémarrés (`sonarqube_db`
puis `sonarqube`, UP en ~20 s). L'analyse en base **précédait donc le code de
cette task** — le QG ERROR affiché au départ ne lui était pas imputable.
Deux scans complets exécutés sur la branche (build Release + 5 passes OpenCover).

### KPI — baseline (analyse périmée, 4 jours) → final (branche task-186)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| bugs | 2 | 2 | = |
| vulnerabilities | 0 | 0 | = |
| code_smells | 69 | 71 | +2 |
| security_hotspots | 15 | 15 | = |
| coverage | 88,1 % | 87,8 % | −0,3 |
| duplicated_lines_density | 0,3 % | 0,3 % | = |
| reliability_rating | 3.0 | 3.0 | = |
| security_rating | 1.0 | 1.0 | = |
| sqale_rating | 1.0 | 1.0 | = |
| **issues totales** | **75** | **73** | **−2** |

`code_smells` monte de 2 alors que le total d'issues baisse de 2 : la baseline
est une photo d'il y a quatre jours qui ne contient pas le code de cette task,
les deux colonnes ne sont donc pas strictement comparables. Le chiffre qui
compte est le suivant.

### Findings sur les fichiers touchés : 3 → 1

| Règle | Fichier | Verdict |
|---|---|---|
| `S3776` cognitive complexity 16/15 | `AuditTraceRepository:118` | **corrigé** — introduit par ma propre condition de filtre (15 → 16). Extrait dans `ApplyActionTypeFilter`. La règle est blacklistée du *hunting* (`/sonar-s3776`), mais franchir soi-même le seuil n'est pas trouver une dette existante. |
| `S134` imbrication > 3 | `RedisAuditSpillStore:114` | **corrigé** — désérialisation extraite dans `TryDeserialize`, boucle de drainage remise à plat. |
| `S1067` 11 opérateurs conditionnels | `AuditTraceRepository:158` | **non corrigé, non imputable** — présent **à l'identique sur `origin/develop`** (filtre de recherche `ILike`, lignes 158-163). Dette antérieure, hors périmètre. |

### Quality Gate : ERROR — et pourquoi ce n'est pas cette task

| Condition | État | Valeur |
|---|---|---|
| `new_coverage` | OK | 87,6 % (seuil 80) |
| `new_duplicated_lines_density` | OK | 0,049 % (seuil 3) |
| `new_security_hotspots_reviewed` | **ERROR** | 0 % (seuil 100) |
| `new_violations` | **ERROR** | 72 (seuil 0) |

Les 15 *security hotspots* non revus et les 72 `new_violations` sont
**antérieurs** : la *new-code period* du projet inclut des tasks déjà mergées
(constat déjà consigné en mémoire). Après correction, **mes fichiers ne portent
plus qu'une seule issue, et elle est pré-existante sur `develop`**. Le total
projet passe de 75 à 73.

**Best-effort assumé** : une itération, les deux findings imputables corrigés,
les findings antérieurs acceptés. Pas de chasse à la dette existante — ce n'est
pas le rôle de cette étape.

### Note sur la suite de tests

Trois exécutions complètes pendant cette étape, trois résultats différents :
0 rouge, puis 1 (`ImapServiceTests` télémétrie), puis 1 (`MailExportServiceTests`
PDF), puis 7 en Release. Aucun ne se répète. C'est exactement le défaut décrit
par **task-291** (non-déterminisme sur trois assemblies, parquée sur fail-fast).
La validation qui fait foi pour cette task est la passe Debug complète
post-correctifs : **1 seul rouge**, `MailExportServiceTests.BuildPdfWithout…`,
flaky déjà documenté. À noter aussi : `--artifacts-path` produit ~107 faux
rouges (il casse les tests qui scannent les sources) — ne pas l'utiliser pour la
suite complète.


## Lint log — client-angular — 2026-09-08

Mode A (chaîné). Scope `mss-lib` : mes changements étant **non commités**
(repo code-only), `nx affected --base=origin/next --head=HEAD` ne les aurait pas
vus — `affected` compare des refs git. `mss-lib` porte l'intégralité du diff et
vit sous `tag:scope:mss`, donc le périmètre de la charte est respecté.

| | Erreurs | Warnings |
|---|---|---|
| Baseline | **3** | 36 |
| Après itération 1 (`--fix`) | **0** | 36 |
| Final | **0** | 36 |

Les 3 erreurs étaient **toutes dans mes fichiers** et **toutes auto-corrigées** :
deux `prettier/prettier` (parenthèses de lambda, retour à la ligne) et un
`jsdoc/require-param`. Une seule itération a suffi.

Validation anti-régression après correction : `nx test mss-lib` **334 tests
verts** (43 fichiers), `nx build mss --configuration=development` vert.

### Une correction manuelle, qui n'entre pas dans la boucle de conventions

L'auto-fixer de `jsdoc/require-param` a **ajouté** `@param traceInput` sans
**retirer** le `@param trace` devenu obsolète après mon renommage de paramètre :
la documentation se retrouvait contradictoire tout en passant le lint. J'ai
supprimé le renommage inutile (`traceInput` + `const trace = traceInput`,
vestige d'une factorisation) et remis un JSDoc juste.

Ce n'est **pas** une règle corrigée manuellement au sens du protocole de
`conventions/angular.md` — le lint était déjà à zéro erreur avant cette
retouche, qui relève de la qualité, pas du lint. **Aucune entrée ajoutée** :
gonfler ce fichier avec des non-récidives le rendrait illisible, et les fixes de
l'auto-fixer sont explicitement exclus du comptage.

Les 36 warnings restants (`jsdoc/require-example`, `max-lines`) sont
**antérieurs** et hors de mes fichiers — best-effort, acceptés.

**Code-only** : aucune opération git sur `client-angular`. Les fichiers restent
modifiés dans l'arbre de travail ; branche, commit, push et PR TFS appartiennent
à l'humain. Les deux `environment.ts` modifiés au pré-flight sont du WIP humain,
préservés intacts.


## Lint mobile log — 2026-09-08

**Skip propre.** `client-mobile` n'est pas listé dans `**Repos**`, son arbre de
travail est vide de modifications et il est resté sur `develop`. Aucune branche
créée par `/start`, aucun code écrit par `/develop` : il n'y a rien à linter.

Le skip est **mesuré** (`--status skipped`) plutôt que passé sous silence —
sinon on ne distinguerait plus « gratuit » de « pas mesuré » dans le journal de
coût du cycle.


## Visual verify log — 2026-09-08

**Skip propre.** `client-mobile` n'est pas dans le périmètre de la task, aucun
écran mobile n'a été touché, et la task ne porte aucun `## Stitch design log`.
Ni serveur `ng serve` démarré, ni capture Playwright : il n'y a aucun écran à
vérifier.

Les deux écrans d'audit impactés par cette task vivent dans **`client-blazor`**
et **`client-angular`**, que `/verify-visual` ne couvre pas (v1 = `client-mobile`
uniquement). Leur vérification est donc **manuelle**, et le plan de test le
prévoit explicitement aux étapes 4bis (Blazor) et 4ter (Angular) — dont le
contrôle de décalage d'ordinaux, qui est le point le plus important à l'œil nu
puisqu'aucun test automatique ne croise les deux écrans.

Skip **mesuré** (`--status skipped`) plutôt que silencieux.


## PRs — 2026-09-08

| Repo | PR | Label |
|---|---|---|
| `dtos-mss` | https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/30 | `awaiting-human-merge` |
| `api-mail` | https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/219 | `awaiting-human-merge` |
| `client-blazor` | https://github.com/codengine-technologies/HealthPlatform.Client/pull/72 | `awaiting-human-merge` |

**Ordre de merge imposé** : `dtos-mss` → `api-mail` → `client-blazor`. À
contre-sens, des traces valides remontent étiquetées « Connexion IMAP » (défaut 4).

### `client-angular` — code-only, l'humain gère git et PR TFS

Quatre fichiers modifiés, **non commités**, sur la branche
`feature/nova-rewriting-mss` :

- `front/libs/mss/src/core/models/audit.model.ts` (+ `audit.model.spec.ts`, **nouveau**)
- `front/libs/mss/src/features/audit/components/audit-detail/audit-detail.component.ts`
- `front/libs/mss/src/features/audit/components/audit-filter/audit-filter.component.ts`
- `front/libs/mss/src/features/audit/components/audit-list/audit-list.component.ts`

Validé par la forge : `nx lint mss-lib` **0 erreur**, `nx test mss-lib` **334
tests verts**, `nx build mss --configuration=development` vert. Les deux
`environment.ts` modifiés sont du **WIP humain préservé**, hors de ce travail.

> ⚠️ Le build **production** Angular échoue, indépendamment de cette task :
> `apps/mss/src/environments/environment.prod.ts` est **ni suivi par git ni
> présent** sur cette branche.

### Repos hors automation

`devops`, `psc-proxy-*` : non concernés par cette task.

## Code Review Summary — APPROVED

27 fichiers relus sur quatre repos, **0 blocage**, 2 suggestions non bloquantes
(purge non exercée contre une vraie base ; deux allers-retours Redis dans
`TrySpillAsync`, assumés). Détail dans le body de la PR api-mail (#219).

**Validation finale** : builds verts sur les quatre repos ; `client-blazor` 182
tests, `client-angular` 334 tests, `api-mail` 3709 tests sur 4 assemblies vertes.
Les 5 rouges d'intégration (`*Today*`) sont **vérifiés rouges à l'identique sur
`origin/develop`** — tests dépendants du jour courant, cassés par le passage de
minuit pendant ce cycle, zéro référence à l'audit.


## Couverture d'intégration — complément du 2026-09-08

Les écarts au DOD signalés comme « non écrits » au terme du cycle sont **fermés**
(24 tests, commit `8cf7736`, PR api-mail #219 mise à jour).

| Écart initial | Statut | Où |
|---|---|---|
| Purge non exercée contre une vraie base | **fermé** — 9 tests | `AuditRetentionPurgeIntegrationTests` (PostgreSQL Testcontainers) |
| Rejeu du spill de bout en bout | **fermé** — 8 tests | `AuditSpillIntegrationTests` (Redis Testcontainers) |
| Test d'intégration ZIP | **fermé** — 3 tests | `MailControllerTests` |
| Frontière Serilog sur le même chemin | **fermé** — 4 tests | `AttachmentAuditLogFrontierTests` |

**Suites complètes vertes** : `api.tests` **809** (+7), `integration.tests`
**443** (+17). Les 5 rouges `*Today*` du cycle précédent sont repassés au vert
d'eux-mêmes — confirmation que le diagnostic « passage de minuit » était le bon.

### Pourquoi la purge n'était pas testable là où elle aurait dû l'être

`mss.mail.infrastructure.tests` tourne sur le provider **EF InMemory**, qui
**n'implémente pas `ExecuteDeleteAsync`**. Une purge couverte uniquement là
aurait été un test n'exécutant jamais l'instruction qu'il prétend vérifier —
c'est exactement la réserve formulée à la revue de code. Ce que seul un vrai
PostgreSQL pouvait établir : que la suppression visant une **sous-requête**
`Take(batchSize)` se traduit en SQL valide, propriété du provider et non de
l'expression C#.

### Ce que la première exécution a rendu explicite

La purge **n'est pas scopée par `UserId`** : les lignes semées par un test
étaient retirées par la passe du suivant. C'est le **comportement correct** —
une base par praticien, donc le contexte *est* le tenant. Un test le documente
désormais, avec sa contrepartie : ajouter un prédicat `UserId` à la purge
rendrait les traces **orphelines** (celles dont la ligne utilisateur a disparu,
cf. task-020) impurgeables à jamais. La lecture, elle, filtre bien par `UserId`
— et c'est précisément pourquoi les deux diffèrent.

### Le test qu'aucune doublure ne pouvait remplacer

Une trace déversée porte son **routage vers la base praticien** dans trois
propriétés `[NotMapped]`. Si la sérialisation les perdait, les traces rejouées
seraient persistées **dans la mauvaise base** — une écriture inter-tenants
silencieuse dans une plateforme de santé. Les tests unitaires substituent
`IAuditSpillStore` : ils prouvent la *décision* de dérouter, jamais ce qui
survit au round-trip. Vérifié contre un vrai Redis.

### Une question ouverte, non tranchée ici

La ligne `LogDebug` du téléchargement unitaire journalise le **nom de fichier**
de la pièce jointe (`Attachment={Attachment}`, `MailController`). Le garde-fou
de task-184 (`SensitiveLogTemplateScanTests`) interdit `{Ins}`, `{PatientName}`,
`{LastName}`, `{Query}`… mais **pas** `{Attachment}` : la doctrine encodée du
projet ne considère donc pas un nom de pièce jointe comme identifiant. Or un
fichier peut s'appeler `DUPONT_Jean_biologie.pdf`.

Les tests de frontière **n'assertent pas** ce point — ni dans un sens ni dans
l'autre. Le pinner reviendrait à bénir un comportement, le corriger à trancher
une doctrine ; ni l'un ni l'autre n'appartient à une task de complément de
couverture. **À arbitrer.** La route ZIP, elle, est déjà volumétrique (un
compteur, jamais les noms) et un test le vérifie.
