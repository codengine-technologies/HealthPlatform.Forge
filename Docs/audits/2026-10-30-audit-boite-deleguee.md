# Audit du périmètre « boîte déléguée » — 2026-10-30

> Revue en lecture seule, menée en cinq axes parallèles :
> 1. rattachement et registre ;
> 2. accès et sessions ;
> 3. données de la boîte et données de la personne ;
> 4. imputation et envois ;
> 5. mobile et weda2.
>
> Base de code : api-mail `60deec50` (`feat/task-407-…`), mobile `d54017a`, weda2
> `feature/nova-mss-weda-integration` (arbre local). **✔ = relu et confirmé dans le code par
> l'orchestrateur** ; *rapporté* = constat d'un axe, non relu ligne à ligne.

## Critique

| # | Constat | Où | Scénario | Vérif. |
|---|---|---|---|---|
| C1 | Le **cache patient par INS est commun à toutes les boîtes de la plateforme** : la clé `patient:ins:{hash(INS)}` ne nomme pas la base, et le cache Redis n'ajoute aucun préfixe. | `PatientRepository.cs:53-93` (`GetByInsAsync`), route `POST /patients/resolve` | Le Dr A résout le patient P : sa fiche est en cache 5 min. Pendant ce temps, le Dr B, sans lien avec A, demande le même INS et **reçoit la fiche de A** : identité, naissance, identifiant technique. Il apprend aussi que P est suivi ailleurs. | ✔ |

## Majeurs — règle 14, sécurité, données de santé

| # | Constat | Où | Scénario | Vérif. |
|---|---|---|---|---|
| M1 | **Mobile : la déconnexion ne vide ni la boîte ouverte ni les états de la boîte.** `LogoutService.run()` n'appelle pas `MailboxSessionService.clear()`, et `mailboxGuard` laisse passer dès que `current()` est posé. | `logout.service.ts:53-63`, `mailbox.guard.ts:24` | Sur une tablette partagée, le Dr A se déconnecte. Le Dr B se connecte par e-CPS (CIBA, sans rechargement) et **arrive dans la boîte de A**, avec ses dossiers et ses messages en mémoire. | ✔ |
| M2 | **La connexion IMAP de fond est mise en commun par boîte, sans la personne.** | `BackgroundImapConnectionRegistry.cs:52-56`, `BackgroundImapService.cs` | Un délégataire lance la première synchro : la connexion de fond est authentifiée avec son jeton. Il est révoqué. Les synchros suivantes, y compris celles du titulaire, réutilisent cette session : les actes partent sous l'identité d'un révoqué. | ✔ (clé) ; impact *plausible* |
| M3 | **La revérification d'accès des flux SSE échoue ouverte.** Toute exception autre qu'une annulation arrête la surveillance, mais le flux continue, car les tâches sont jointes par `WhenAll`. | `SseHelper.cs:41-64`, `MailEventsController.cs:133-146` | Le proxy PSC est indisponible un instant au moment de la revérification : le délégataire continue de recevoir les événements de la boîte, même après sa révocation. | ✔ |
| M4 | **Les routes `api/v1/diagnostics/*` ne sont ni gardées ni tracées.** Elles sont annoncées « réservées à l'exploitation », mais aucun contrôle de rôle ou d'environnement ne les protège. `test-similarity` rend le corps des documents et l'identité des patients. | `AiDiagnosticsController.cs:43,76,333,412` | Un délégataire envoie `test-similarity {"query":"Dupont"}`, obtient les comptes rendus et les identités, et le journal reste vide. | ✔ |
| M5 | **La lecture d'un message par une deuxième personne n'est jamais tracée.** Le contenu est exempté au motif que « la lecture est tracée au passage à lu ». Or le `\Seen` appartient à la boîte : le second lecteur ne déclenche pas de passage à lu. | `MailController.cs:693` (contenu) et `:643` (résumé) | Le titulaire lit un compte rendu de biologie. Le délégataire le lit ensuite : aucune trace ne le nomme. | ✔ |
| M6 | **Les traces de gestion des boîtes sont rangées dans le journal de la boîte ouverte, pas de la boîte visée.** Concerne le rattachement, le détachement, la réauthentification, la boîte par défaut et les refus. `Impute` complète `MailboxId`, `MailboxAddress` et `ActorRole` avec `??=` depuis le contexte. | `AuditService.cs:118-132`, `MailboxManagementService.cs:254, 347, 417, 496` | Boîte A ouverte, Cyril détache B : la trace part dans le journal de A, avec son rôle sur A. Les personnes de B ne la voient pas. | ✔ |
| M7 | **Cinq actions marquées `[TracedInCode]` ne tracent rien** : non-lu, marquage lu ou non-lu en masse, signalé et non signalé. Le rejeu hors ligne ne trace pas non plus. Le test d'architecture ne le voit pas : il cherche la chaîne `AuditActionType.X` n'importe où dans le code. | `EmailFlagService.cs` (2 `Trace` seulement), `EveryControllerActionIsTracedTests.cs:61-66` | Un délégataire retire l'urgence d'un message signalé par le titulaire : rien n'apparaît au journal. | ✔ |
| M8 | **Mobile : le flux de l'assistant IA envoie l'adresse du compte en `Client-Email`.** C'est la même classe de défaut que le From corrigé en task-407. | `mss-api.service.ts:872-879` | Un délégataire, ou un membre d'une boîte organisationnelle, ouvre l'assistant : 403 ou 404, ou une conversation dans une autre boîte. | ✔ |
| M9 | **Un délégataire peut modifier l'identité d'expéditeur de la boîte** dès qu'aucun titulaire n'est « actif », par exemple quand le titulaire n'utilise pas ce logiciel ou est « à requalifier ». | `MailboxSenderIdentityService.CanEditAsync` | La secrétaire déléguée change le nom affiché sur la boîte du Dr X. | ✔ (comportement documenté, **à arbitrer**) |
| M10 | **Le rôle n'est requalifié que lors d'une réauthentification déclenchée par une boîte en échec.** Le titulaire est en plus exempté de verdict de l'opérateur, en ligne comme hors ligne. | `MailboxManagementService.cs:413-415, 448-477` ; `MailboxAccessPolicy.cs:46` | L'adresse personnelle d'un titulaire est retirée de l'Annuaire : il reste titulaire, sans verdict, indéfiniment. | ✔ (chemin) ; politique **à arbitrer** |
| M11 | **weda2 : quand l'Annuaire est indisponible, l'adresse désignée par Weda est préremplie dans le champ « déléguée », et le serveur accepte la délégation sans contrôle de liste.** | `attach-mailbox-form.component.ts:142-153` ; `MailboxManagementService.cs:206-217` | Le Dr X rattache sa propre boîte comme délégataire : sans hors-ligne et avec le mauvais rôle. | ✔ (serveur) ; client *rapporté* |
| M12 | **Sonde de l'opérateur : ni second essai sur jeton refusé, ni appel unique au renouvellement du verdict.** Une connexion IMAP réutilisée ne renouvelle pas le verdict. | `OperatorAccessProbe.cs:52-74`, `MailboxAccessGate.cs:104-117` | Un jeton périmé suspend à tort un délégataire. Chaque rafale de requêtes à l'expiration lance 5 à 10 connexions opérateur, au risque d'un verrouillage du compte comme sur Mailiz. | *plausible* |
| M13 | **Les données personnelles d'avant task-404 ne sont pas reprises** : réglages, signatures et envois mis de côté restent sur la ligne « boîte ». | migration `AddUserAuthenticationSubject`, `BaseRepository.cs:162` | Un envoi mis de côté avant la mise à jour n'est plus jamais proposé ni rejoué. | *plausible* ; dépend des bases existantes en production |
| M14 | **Le préremplissage d'un membre écrit sa propre structure comme identité de la boîte organisationnelle.** | `MailboxPrefillService.cs:180-184` | Tous les membres de l'hôpital H envoient sous le nom du cabinet C d'un des membres. | *rapporté* |

## Moyens

| # | Constat | Vérif. |
|---|---|---|
| m1 | Les préférences de notification appliquées sont celles de la personne qui a lancé la synchro ; les alertes vont ensuite à toute la boîte (`NewMailNotifier.cs:84`). | ✔ |
| m2 | L'historique de recherche est indexé par la boîte : il est partagé entre titulaire et délégataires, et son effacement n'est pas tracé (`SearchController.cs:125,245,263`). | ✔ |
| m3 | Les conversations de l'assistant IA sont indexées par la boîte (`AiConversationService.cs:115,183,411,420`). | *rapporté* |
| m4 | Brouillons : pas de contrôle de version. Une modification faite pendant l'envoi d'un autre est perdue, et une suppression est annulée par le chemin d'échec (`DraftService.cs:117-134, 191-205, 286-289`). | *rapporté* |
| m5 | Mobile : la conversation IA survit au changement de boîte (le contenu de A est rouvert dans B). L'onglet Patients garde la liste de A, les widgets de l'accueil gardent les données de A, et les réglages en cache écrivent ceux de A dans B. | *rapporté* |
| m6 | Mobile : la modale de rédaction et la modale IA restent ouvertes au-dessus de l'écran « accès suspendu ». | *rapporté* |
| m7 | Mobile et weda2 : une requête « épinglée » (confirmation de rattachement) refusée suspend la boîte ouverte, et non la boîte visée. | *rapporté* |
| m8 | Les traces de refus d'accès n'ont ni nom ni rôle, et hors ligne ni RPPS (le verrou passe avant l'enrichissement du contexte). | *rapporté* |
| m9 | Les consommateurs du bus écrivent des étiquettes et des contacts sans aucune trace, pas même comme acte système. | *rapporté* |
| m10 | La réception et le traitement des CDA sont imputés à la personne qui a lancé la synchro, au lieu d'un acte système. | *rapporté* |
| m11 | La consultation d'une fiche patient est tracée sans objet : l'INS ou l'identifiant patient est dans le corps de la requête, pas dans la trace. | *rapporté* |
| m12 | L'INS apparaît dans les journaux techniques : `SmtpService` journalise au niveau Information les destinataires `{INS}@patient.mssante.fr`. | *rapporté* |
| m13 | La recherche LDAP tronquée (limite de taille) est traitée comme complète : requalification à tort, ou délégation acceptée. | ✔ |
| m14 | Un rattachement refusé par la sonde IMAP n'est pas tracé. | ✔ |

## Mineurs

- La requalification ignore le type d'adresse : un titulaire peut rester titulaire sur une adresse
  devenue organisationnelle.
- Requalifier par l'Annuaire une boîte en échec répond 201 alors que la boîte reste inutilisable.
- Deux premiers rattachements en parallèle produisent un faux 409.
- `UserSettings.UserId` n'a pas d'index unique.
- `Reset()` n'efface pas les champs de task-405, et le test de parité ne le voit pas.
- La clé Redis `psc:person-name:{proxy_session_id}` contient le cookie de session en clair.
- Détacher ou suspendre ne coupe ni les sessions ni la synchro en cours.
- `MaxSessionsPerMailbox` est partagé entre toutes les personnes d'une boîte.
- Mettre en pause ou relancer la synchro agit sur toute la boîte.
- Les copies des bases par personne d'avant task-404 ne sont pas purgées.
- `{{SenderRPPS}}` (weda2) est tiré de la partie locale de l'adresse.
- weda2 ne rouvre pas le flux de notifications après « Réessayer ».
- La détection du dossier « envoyés » se fait par la sous-chaîne `sent`.
- Le journal expose aux co-utilisateurs l'IP, l'agent utilisateur et le `sub` Keycloak.

## Vérifié et sain (extraits)

- **Rôle et rattachement** :
  - la saisie libre donne toujours un délégataire ;
  - la liste « Mes boîtes » est relue côté serveur ;
  - la sonde passe avant toute écriture, avec le jeton PSC de la personne.
- **Une base par adresse** : nom dérivé de l'adresse seule, contraintes d'unicité, clé étrangère
  composite.
- **Verrou d'accès** :
  - échec fermé si Redis tombe ;
  - délégataire et membre sans hors-ligne ;
  - sélection de boîte contrôlée contre le registre.
- **Envois** : tous passent par `SmtpService` ou `MdnService` (direct, brouillon, confirmé,
  annule-et-remplace, IHE XDM, accusé de lecture). L'archive « Envoyés » porte le Sender.
- **Journal** : RLS par boîte, et un délégataire refusé n'y a pas accès.
- **Données** : signatures, réglages et actions en attente sont propres à chaque personne.

## Décisions humaines (2026-10-30) et découpage en tasks

| Point | Décision |
|---|---|
| M4 (routes de diagnostic) | Contrôleur retiré, ainsi que le code qui ne sert qu'à lui |
| M9 (identité d'expéditeur de la boîte) | Titulaire seul, toujours |
| M10 (requalification, titulaire exempté de verdict) | Inchangé. Risque accepté, consigné dans E020. |
| M13 (données d'avant task-404) | Pas de reprise, aucune base en production |
| m2 / m3 (historique de recherche, conversations IA) | Recherche à la personne, IA à la boîte |
| Journal (IP, navigateur, identifiant visibles des co-utilisateurs) | Tout montrer : comportement accepté |

| Task | Couvre |
|---|---|
| task-410 — cache patient par INS cloisonné par boîte | C1 |
| task-411 — accès et sessions serveur | ABANDONNÉE (décision humaine du 2026-10-30, task supprimée) — M2, M3, M4, M12 ; détachement, suspension et déconnexion qui coupent tout ; clés du pool, `psc:person-name`, quotas, pause et reprise |
| task-412 — clients : déconnexion et changement de boîte | M1, M8, m5, m6, m7 ; dossier « envoyés », `{{SenderRPPS}}`, flux de notifications weda2 |
| task-413 — traçabilité | ABANDONNÉE (décision humaine du 2026-10-30, task supprimée) — M5, M6, M7, m8 à m12, m14 |
| task-414 — données propres à la personne | ABANDONNÉE (décision humaine du 2026-10-30, task supprimée) — m1 à m4, index de `UserSettings` |
| task-415 — rattachement, registre et identité | ABANDONNÉE (décision humaine du 2026-10-30, task supprimée) — M9, M11, M14, m13 ; requalification par type, boîte en échec, rattachements simultanés, `Reset()`, contournement de test ; M10 et M13 documentés |

> **2026-10-30 — décision humaine** : task-411, task-413, task-414 et task-415 ne seront pas développées
> et ont été supprimées. Les constats qu'elles couvraient restent ouverts, sans task.

Copies des bases par personne d'avant task-404 : sans objet, aucune base en production (M13).
