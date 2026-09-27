# questions/task-320.md — `/review` : CHANGES REQUESTED

> **✅ Résolu le 2026-09-27** — les trois points bloquants ont été corrigés par une reprise de `/develop` (api-mail 9f78a225, client-blazor 4b98cbd, client-mobile 731baa9, client-angular non commité) ; second `/review` : APPROVED, PRs ouvertes. Les suggestions non bloquantes restent à arbitrer.

**Étape** : `/review task-320` (après `/develop` → `/sonar` → `/lint-angular` → `/lint-mobile` → `/verify-visual`).
**Date** : 2026-09-27.
**Décision attendue** : aucune décision métier. Les trois défauts ci-dessous sont techniques et leur correctif est connu. Il faut autoriser leur correction (relancer `/develop task-320` sur les mêmes branches), puis relancer `/review task-320`.

## Ce qui est vert

- Build + tests, revalidés par `/review` sur l'état poussé :
  - api-mail : 5 621 passés, 16 ignorés, 0 échec
  - client-blazor : 309 passés, 2 ignorés, 0 échec
  - client-mobile : 912 / 912
  - client-angular : build OK, tests OK sur 11 projets
  - dtos-mss : build OK
- Sonar : Quality Gate OK, new_coverage 98.8 %, 0 issue new-code.
- **La promesse centrale de l'US tient** (relecture api-mail) : aucun chemin ne permet à un message rédigé de partir sans une confirmation faite pendant une session PSC. Rejeu supprimé, route brouillon fermée hors ligne, `X-PSC-Token` jamais lu, réclamation atomique contre la double confirmation.

## Défauts bloquants (❌)

### 1. api-mail — un message réclamé reste bloqué en `Processing` si l'envoi LÈVE une exception

- **Où** : `Api/Mail/src/Api/Controllers/V1/MailController.cs`, `ConfirmPendingEmailAsync` (~l. 1540-1570).
- **Le défaut** : la ligne n'est rendue (`ReleasePendingEmailAsync`) que sur `!sendResult.IsSuccess`. Aucun `try/catch/finally` autour de l'envoi. Or `SmtpService.SendMailAsync` lève dans des cas réels :
  - la garde d'opposition patient `oppositionGuard.EnsureSendAllowedAsync` (`ConflictException` → 409), de façon **déterministe** pour un message adressé à un patient opposé ;
  - la construction MIME ;
  - l'acquisition de session ;
  - une annulation client (`OperationCanceledException`).
- **Conséquence** : aucun code ne remet jamais une ligne `Processing` en attente. Le message disparaît de la liste, du compteur et de l'annulation. **Le praticien perd son message sans rien voir.**
- **Correctif** : envelopper l'envoi pour rendre la ligne quand il lève, avant de relancer l'exception. Sur une annulation, rendre avec `CancellationToken.None`. Test unitaire : envoi qui lève `ConflictException` → ligne rendue + 409.

### 2. XSS dans « Revoir » — le corps HTML d'un message prêt à partir n'est pas assaini

- **Où** :
  - backend : `PendingActionService.GetPendingEmailAsync`, qui rend le `MailDto` tel que le client l'a posté ;
  - Blazor : `PendingEmailsDialog.razor` (~l. 363-367, 412) utilise `loadHtmlInShadowDom`, une iframe blob **sans attribut `sandbox`**, donc exécutée dans l'origine de l'application (le commentaire « iframe sandboxée » est faux).
- **Pourquoi c'est bloquant** : c'est exactement la menace que l'US cite (jeton Keycloak volé, session laissée ouverte).
  1. Un attaquant muni du seul bearer Keycloak met en file un message dont `BodyHtml` contient un script.
  2. Le médecin, carte présente, clique « Revoir ».
  3. Le script s'exécute, peut lui-même appeler `POST pending-emails/{id}/send` (le cookie `proxy_session_id` part avec la requête), et contourne donc le geste « un message, une confirmation ».
- **Correctif** :
  - côté serveur, passer `BodyHtml` dans l'`IHtmlBodySanitizer` existant (task-088) dans `GetPendingEmailAsync`, ce qui protège les trois fronts d'un coup ;
  - côté Blazor, en défense en profondeur, iframe `sandbox` sans `allow-scripts` ni `allow-same-origin` pour ce panneau, et commentaire corrigé.
- Angular (assainisseur Angular + blocage du contenu distant) et mobile (rendu en texte via `DOMParser` / `textContent`) ne sont **pas** exposés.

### 3. Les trois fronts — un brouillon mis de côté par le serveur est annoncé « Message envoyé »

- **Où** :
  - mobile : `mail-compose.component.ts` (~l. 912-921) et `mss-api.service.ts:834` (`sendDraft(): Observable<void>`) ;
  - Angular : `mail-compose.component.ts:890-904` (`executeSendDraft`) et `mss-api.service.ts:2276` ;
  - Blazor : `NewMailComponent.razor:1063-1085` et `DraftService.cs:94` (le 202 est lu comme un succès).
- **Le défaut** : chaque front choisit la route brouillon selon son indicateur local « en ligne », lu une fois et **périmé** quand la session PSC expire ou que le proxy tombe en cours de journée. Le serveur, lui, répond désormais `202 {awaitingConfirmation}` sur `POST /drafts/{id}/send` hors ligne (correctif serveur de ce cycle, 67cbd0fd). Les trois fronts ignorent ce corps et affichent « envoyé ».
- **Conséquence** : le message n'est pas perdu, il attend dans la liste. Mais **le médecin croit qu'un message médical est parti** alors qu'il ne l'est pas, ce qui contredit RG-3 et RG-8.
- **Correctif** : lire la réponse de `sendDraft` et, sur `awaitingConfirmation`, afficher « Message prêt à partir » et rafraîchir le compteur, comme le chemin `sendmail` le fait déjà. Un test par front : « route brouillon, le serveur répond 202 → prêt à partir, pas envoyé ».

## Suggestions non bloquantes (à arbitrer, pas nécessaires au merge)

- **MDN / accusé de lecture** (`SendReadReceiptAsync`, `MdnService`) : part en SMTP sans contrôle du mode, préexistant. C'est une notification automatique, pas un message rédigé, mais l'US dit « aucun message ne part sans sa carte ». **Décision PO** : garde hors ligne (401), ou follow-up.
- **Rétention** : les lignes `Completed` gardent le message complet (corps, pièces jointes) indéfiniment en base praticien. L'AIPD parle de stockage « jusqu'à confirmation ou annulation ». **Décision** : vider `Payload` à la confirmation, ou purger après N jours.
- **Fraîcheur du garde** : `GetAccessTokenAsync` sert le jeton en cache. « Session valide à l'instant » veut donc dire en réalité « dans la durée de vie du jeton », comme pour l'envoi en ligne existant. À documenter, ou à forcer d'une option de contournement du cache.
- **401 `PSC_SESSION_*` et rafraîchissement Keycloak** : Blazor ne rafraîchit plus sur ces codes. Le mobile rafraîchit et rejoue, sans déconnexion dans le cas normal. Angular est sûr aujourd'hui (intercepteur non appliqué à l'API MSS), mais le risque reste latent. Porter l'exclusion Blazor en follow-up.
- **Charge** : la bannière Blazor interroge `connection/status` toutes les 10 s, en ligne comme hors ligne, et un toast se répète si le backend est instable. Le widget Angular hors ligne interroge la liste complète toutes les 10 s, et la bannière mobile relit l'état deux fois par changement d'onglet.
- **Blazor « Revoir »** : une réponse tardive peut afficher le contenu d'un message sous une autre ligne (clics rapides sur deux « Revoir »).
- **Processus arrêté entre la réclamation et la clôture** : résiduel rare. Le choix sûr est « ne jamais renvoyer tout seul », avec une récupération à prévoir en follow-up.

## État des repos (rien n'est perdu, rien n'est mergé)

| Repo | Branche | État |
|---|---|---|
| dtos-mss | feat/task-320-envoi-confirme-avec-carte | poussé, NuGet 489.0.0 publié |
| api-mail | feat/task-320-envoi-confirme-avec-carte | poussé (a939435d), à jour de develop |
| client-blazor | feat/task-320-envoi-confirme-avec-carte | poussé (87974c2) |
| client-mobile | feat/task-320-envoi-confirme-avec-carte | poussé (ce57c7c) |
| client-angular | feature/nova-rewriting-mss | code-only, **non commité** (humain) |

Aucune PR ouverte. La task reste en `wip-task-320.md`.
