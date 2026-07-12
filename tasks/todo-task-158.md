# todo-task-158.md — Suppression & déplacement d'emails résilients (repli COPY quand le serveur IMAP rejette MOVE)

**Repos**: api-mail
**Dependencies**: none

> US **mono-couche backend** (exception justifiée, cf. CLAUDE.md racine) : le
> correctif est purement dans la couche de transport IMAP d'`api-mail`. Les
> contrats DTO et les endpoints exposés sont **inchangés** — les frontends
> (blazor / angular / mobile) appellent exactement les mêmes routes
> (`DELETE .../emails/{uid}`, `PUT .../emails/{uid}/move`) sans aucune
> modification. Aucun changement `dtos-mss`.

## Objective

Rendre la **suppression** (déplacement vers la Corbeille) et le **déplacement
vers un dossier** d'un email **fiables**, y compris sur les boîtes MSSanté dont
la commande IMAP `MOVE` est défaillante — **sans régresser** le comportement
actuel sur les boîtes où `MOVE` fonctionne.

> ⚠️ **Particularité liée au type de boîte aux lettres.** Le problème **n'est
> pas universel** : sur **une autre boîte MSSanté**, la suppression et le
> déplacement **fonctionnent parfaitement** (le `MOVE` passe). L'échec est donc
> une **caractéristique propre à certaines boîtes / certains opérateurs**
> MSSanté, pas un défaut général du serveur. En conséquence, **le code actuel
> (MOVE) reste le comportement par défaut** et le repli COPY n'intervient
> **qu'en cas d'échec** du `MOVE`.

Constat (boîte du compte `robert.specialiste0060694@…`, env **formation**) : le
serveur **annonce** la capacité `MOVE` (RFC 6851) mais la **rejette
systématiquement** avec un `NO — Internal error occurred` (~6 s), quelle que
soit la destination (Corbeille **ou** dossier classique). Notre code fait
aveuglément confiance à la capacité annoncée → sur **cette** boîte, toute
suppression/déplacement échoue en **500**, l'email reste en place, après 6 à
25 s d'attente. Sur une autre boîte, tout marche.

Objectif : **conserver le chemin `MOVE` par défaut** (rapide, atomique, OK sur
la majorité des boîtes) et **ajouter un repli automatique** sur `COPY` +
marquage `\Deleted` + `EXPUNGE` (COPY = cœur RFC 3501, universellement
supporté) **déclenché uniquement quand le `MOVE` échoue**, sur les quatre
chemins concernés, sans jamais faire transiter le corps du message par l'API
(invariant task-068 préservé — COPY est server-side).

## Contexte / preuves (Seq — env formation, client émulateur Android)

- `DELETE /api/v1/mail/folders/INBOX/emails/8111|8114|8115` → **500** (11–25 s)
  via `ImapService.MoveSingleToTrashViaServerAsync`
  ([ImapService.cs:2148](../Api/Mail/src/Application/Services/Implementation/ImapService.cs#L2148)).
- `PUT /api/v1/mail/folders/INBOX/emails/8418/move` (INBOX → **Bio**, dossier
  classique) → **500** (6,5 s) via `ImapFolderService.MoveEmailAsync`
  ([ImapFolderService.cs:492](../Api/Mail/src/Application/Services/Implementation/ImapFolderService.cs#L492)).
- Exception commune :
  `MailKit.Net.Imap.ImapCommandException: The IMAP server replied to the 'MOVE'
  command with a 'NO' response: Internal error occurred.`

Chemins à traiter (les 4) :
- suppression simple → `MoveSingleToTrashViaServerAsync` (ImapService.cs:2139)
- suppression en masse → `MoveEmailsToTrashAsync` / `MoveToAsync` (ImapService.cs:2310)
- déplacement simple → `MoveEmailAsync` (ImapFolderService.cs:492)
- déplacement en masse → `BulkMoveEmailsAsync` (ImapFolderService.cs:569)

## Comportement attendu (acceptation)

- Étant donné un PS connecté à sa boîte MSSanté **dont le serveur rejette la
  commande MOVE**, quand il **supprime** un email, alors l'email est déplacé
  vers la Corbeille et disparaît de l'INBOX, **sans erreur**.
- Étant donné le même contexte, quand il **déplace** un email vers un dossier,
  alors l'email apparaît dans le dossier cible et disparaît du dossier source,
  **sans erreur**.
- Étant donné un serveur IMAP **conforme** (MOVE fonctionnel), le comportement
  rapide (MOVE atomique) est **conservé** — pas de régression.
- Le **corps** de l'email ne transite **jamais** par l'API (COPY/MOVE
  server-side — invariant task-068).
- La **cascade Corbeille** (suppression du lien patient + documents rattachés,
  reconstruite à la restauration) reste déclenchée à la suppression.
- Si `COPY` échoue **aussi** (serveur profondément cassé), l'échec est remonté
  proprement en `ProblemDetails` RFC 7807 (pas de 500 brut) et tracé pour
  escalade — le repli est ainsi **auto-validant**.

## Definition of Done

- [ ] Build passes (0 erreurs) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 échecs) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] **`MOVE` reste le chemin par défaut** — comportement actuel **inchangé** sur les boîtes où il fonctionne ; le repli n'est **jamais** emprunté quand `MOVE` réussit
- [ ] Repli **automatique** `COPY + \Deleted + EXPUNGE` déclenché **uniquement** sur `ImapCommandException` du `MOVE`, sur les **4 chemins** (delete simple/masse, move simple/masse)
- [ ] *(Optionnel, secondaire)* option de config (ex. `Imap:PreferCopyOverMove`, **défaut désactivé**) pour forcer `COPY` d'emblée sur une boîte/env dont le `MOVE` est connu défaillant (évite la pénalité ~6 s par opération) — le mécanisme **principal** reste le repli automatique sur échec
- [ ] Test unitaire : `MOVE` rejeté (`ImapCommandException`) → `COPY` appelé → `\Deleted` posé → succès (mock `IImapClientWrapper` / `IMailFolder`), pour **suppression ET déplacement**
- [ ] Test unitaire : quand `MOVE` réussit, `COPY` **n'est pas** appelé (non-régression sur les boîtes au `MOVE` fonctionnel)
- [ ] Test : le corps du message ne transite pas par l'API (aucun fetch/download du contenu dans le chemin de repli)
- [ ] Test : échec de `COPY` **aussi** → erreur mappée en `ProblemDetails` RFC 7807 (règle 12), pas de 500 brut
- [ ] Audit `MailDelete` / `MailMove` tracé avec le chemin réellement emprunté (MOVE vs repli COPY) et le résultat
- [ ] Aucune donnée de santé en clair dans les logs (INS, NIR, NIA, contenu CDA / MSSanté, objet d'email sensible)

## Manual Test Plan

- Lancer le backend api-mail connecté à la **boîte MSSanté formation** (serveur au `MOVE` défaillant).
- Depuis un client (émulateur mobile ou web) :
  - **Supprimer** un email de l'INBOX → il part en **Corbeille**, disparaît de l'INBOX, **aucune erreur** affichée.
  - **Déplacer** un email INBOX → **Bio** → il apparaît dans Bio, disparaît de l'INBOX.
- Vérifier dans **Seq** : plus aucun **500** sur `DELETE .../emails/{uid}` ni `PUT .../emails/{uid}/move` ; une trace d'audit indique le **repli COPY** effectivement emprunté.
- Vérifier la **Corbeille** : restaurer l'email supprimé → le lien patient et les documents rattachés sont reconstruits (cascade).
- (Idéalement) rejouer sur un serveur IMAP conforme (MOVE OK) → confirmer que `MOVE` est toujours utilisé (pas de régression).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie sécurisée de santé MSSanté).
- **Vague Ségur** : V2 (socle MSSanté).
- **Exigences DSR honorées** : gestion de boîte MSSanté (suppression / rangement de messages) — exigence de **robustesse d'intégration** avec l'opérateur ; non applicable au contenu métier.
- **INS** : non applicable — opération de **transport IMAP**, aucune manipulation d'INS. La cascade Corbeille touche le **lien patient local**, sans modifier ni exposer l'INS.
- **Authentification PS** : PSC / e-CPS (session existante), niveau eIDAS substantiel — **inchangé** par cette US.
- **Habilitations** : inchangé — le PS agit sur **sa propre** boîte MSSanté.
- **Interop CI-SIS** : non applicable — commande de transport IMAP, aucun échange CDA r2 / FHIR / HL7v2.
- **Tracé PGSSI-S** : évènements `MailDelete` et `MailMove` (déjà journalisés) — **enrichis** du chemin réellement emprunté (MOVE / repli COPY) et du statut (succès / échec) ; durée de conservation selon la politique existante.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun (CIM-10 / SNOMED / LOINC / CCAM / NABM / CIS-CIP — sans objet).
- **Hébergement HDS** : oui — environnement HDS existant (boîte MSSanté) ; périmètre **inchangé**, aucune nouvelle donnée hébergée.
- **AIPD / impact RGPD** : inchangé — pas de nouveau traitement, aucune donnée supplémentaire collectée ; correctif de robustesse sur un traitement existant.
