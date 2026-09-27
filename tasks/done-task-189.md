# todo-task-189.md — Durcissement de la surface HTTP : suppression de la purge de développement, corps invalide en 400, plus de GET qui écrit, pagination bornée

**Repos**: api-mail, client-blazor
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe surface HTTP), re-vérifiée le
> 2026-08-23 puis par l'audit de détection de bugs du **2026-09-27**
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, section 2).

> ### Mise à jour du 2026-09-27 — décision humaine et état rejoué sur `develop` @ `14d58398`
>
> - **Décision humaine (2026-09-27) : la purge est SUPPRIMÉE du code**, pas gardée. Elle avait été
>   ajoutée pour faciliter le développement ; elle n'a pas de raison d'exister dans l'API.
>   L'arbitrage « garder derrière un rôle / supprimer » de la version précédente est donc tranché.
> - **Ancienne preuve 5 (trois rejets 403 hors RFC 7807) : CORRIGÉE** — task-303 (`63ba41ad`) et
>   task-308 (`09740e5f`) ont supprimé les réponses écrites à la main ; tous les refus passent par
>   `WriteMailboxProblemAsync` (`UserContextEnricherMiddleware.cs:692-720`) en
>   `application/problem+json`. Retirée du périmètre ; la coordination avec task-184 sur ces chemins est caduque.
> - **Ancienne preuve 4 (pagination) : plus étroite qu'annoncé le 2026-08-23** — les deux sites
>   `embeddings/missing` et `embeddings/reindex-missing` sont bornés depuis task-196
>   (`MedicalDocumentRepository.cs:80`, `Math.Clamp(limit, 1, 1000)`). **Un seul site reste** : `list-emails`.
> - Chemins de fichiers : `src/Infrastructure/Repository/*` est devenu `src/Infrastructure/Repositories/MailDb/*` (task-299).

## Objective

Corriger quatre défauts de la surface HTTP qui rendent l'API destructive, imprévisible ou non conforme
au contrat d'erreur du projet (règle 12, RFC 7807).

**Périmètre repos (justification)** : correctif backend ; `client-blazor` est ajouté **uniquement**
parce que sa page de gestion appelle la route de purge supprimée (bouton et appel de service à retirer).
`client-angular` et `client-mobile` n'appellent pas cette route (vérifié le 2026-09-27).

### Preuve (état actuel du code — `develop` @ `14d58398`)

**1. Une purge de développement exposée à tout praticien authentifié** —
`src/Api/Controllers/V1/MailMaintenanceController.cs:111-139` (attribut de route `:115`) :
```csharp
[HttpDelete("purge-mails")]
public async Task<IActionResult> PurgeMailsAsync()
{
    …
    await context.Database.ExecuteSqlRawAsync("TRUNCATE TABLE \"MailMedicalDocumentBiology\" CASCADE");
    … 6 TRUNCATE au total, dont "Mails" RESTART IDENTITY CASCADE (:128)
```
Aucun `[Authorize(Roles/Policy)]` sur le contrôleur (`:29-31`), aucun contrôle d'environnement, aucune
confirmation ; seul rempart, la politique globale `RequireAuthenticatedUser` (`Program.cs:132-135`).
N'importe quel praticien authentifié peut vider irréversiblement sa base mail (contenus enrichis,
documents CDA, accusés de biologie, liens patients). Le commentaire du contrôleur (`:19`) le présente
comme « admin-only diagnostics » — rien ne l'applique.
Appelant : `client-blazor` — `Src/Modules/Mss/Plugin/Pages/ManagementPage.razor:522` (bouton),
`:573` et `:779-809` (action), via `Src/Modules/Mss/Application/Services/ManagementService.cs:76-97`
et `IManagementService.cs:23`.

**2. Corps de requête invalide ⇒ 500 au lieu de 400** — `src/Api/Program.cs:66` :
`options.SuppressModelStateInvalidFilter = true`. Un corps qui échoue au binding ne produit pas le 400
automatique : l'action s'exécute avec le paramètre à `null`. Le filtre `ModelStateDiagnosticsFilter`
(`Program.cs:54-56`, task-169) **journalise seulement** et ne change pas la réponse. Actions qui
déréférencent le modèle avant toute garde (ancres au 2026-09-27) :
- `AiController.cs` : `CorrectTextAsync` `:49`, `GenerateTemplateAsync` `:102`, `ImproveTextAsync` `:124`, `DetectPlaceholdersAsync` `:148`
- `AiDiagnosticsController.cs` : `TestSimilarityAsync` `:64`, `RecalculateSummaryAsync` `:376` (`EmailUid` est `required uint` : le cas `{"emailUid":""}` s'applique)
- `SearchController.cs` : `SemanticSearchAsync` `:71` (**avant** le test `ModelState` de `:73`), `SearchByPatientAsync` `:139`
- `AiChatController.cs` : `CreateConversationAsync` `:62`
- `PatientsController.cs` : `UpdateOppositionByPatientIdAsync` `:300`, **et `SearchPatients` `:145`** (`filters.LastName` lu avant le test `ModelState` de `:149` — non listée dans la version précédente)
- `MailController.cs` : `EnrichEmailsBackgroundAsync` `:440`, `EnrichEmailsSyncAsync` `:556` (`uids.Count`)
- `SignatureController.cs` : `CreateAsync` `:83`, **et `UpdateAsync` `:122`** (non listée précédemment)
- `MailTemplateController.cs` : `CreateAsync` `:95`, `UpdateAsync` `:127`

Le patron correct existe : `ContactController.cs:35` (`RequireBody`). Même forme que le bug mobile
task-168 (`"id":""` invalide pour un `Guid` ⇒ corps lié à `null` ⇒ NRE).

**3. Une écriture exposée en GET** — `src/Api/Controllers/V1/SettingsController.cs:53-55` : l'action
qui **remplace en bloc** les paramètres du praticien porte `[HttpPost]` **et** `[HttpGet("settings")]`.
La lecture a sa propre route (`[HttpGet("getsettings")]`, `:34`) ; le mappage GET ne sert aucun client
et rend l'écriture éligible au préchargement et au rejeu par navigateurs et proxys.

**4. Pagination non bornée** — `MailMaintenanceController.cs:41` (`[FromQuery] int limit = 100`) puis
`:55` (`.Take(limit)`). Un `limit` négatif atteint PostgreSQL en `LIMIT -1` (500) ; un `limit` énorme
matérialise toute la table. Patron correct : `PatientsController.cs:375` (`Math.Clamp`).

### Contenu attendu

1. **Suppression de la purge** :
   - `api-mail` : action `PurgeMailsAsync` supprimée de `MailMaintenanceController` (la route répond
     **404**) ; commentaire de classe (`:19`) mis à jour ; tests qui la citent mis à jour
     (`tests/mss.mail.api.tests/Controllers/V1/MailMaintenanceControllerTests.cs:54` — ligne `InlineData`
     à retirer ; notes des tests d'intégration `MailMaintenanceControllerIntegrationTests.cs:22, 114` et
     `MailMaintenanceControllerCoverageTests.cs:16` à retirer).
   - `client-blazor` : bouton « Purger » et son action retirés de `ManagementPage.razor`, méthode
     `PurgeMailsAsync` retirée de `IManagementService` / `ManagementService`, libellés Localizer
     associés retirés ; aucun autre élément de la page de gestion modifié.
   - `PurgeMailsResponseDto` (`Dtos/ManagementDtos.cs`, **dtos-mss**) : **laissé en place** — le retirer
     imposerait une publication NuGet et un bump des consommateurs pour aucun gain ; à supprimer lors
     d'une prochaine évolution de contrat.
   - Si une remise à zéro reste utile en développement, elle passe par les outils du poste (recréation
     de la base de l'AppHost), **jamais** par une route de l'API.
2. **Corps invalide ⇒ 400 problem+json** sur toutes les actions listées, par une solution **transverse**
   (filtre ou convention : paramètre `[FromBody]` nul ou `ModelState` invalide ⇒ `ValidationProblemDetails`
   400), plutôt que des gardes recopiées. Vérifier qu'elle ne casse pas les actions qui s'appuient
   volontairement sur `SuppressModelStateInvalidFilter` (lister celles qui testent `ModelState` elles-mêmes).
3. **Retirer le mappage GET** de l'action d'écriture des paramètres (405 attendu).
4. **Borner `limit`** de `list-emails` (`Math.Clamp`, valeurs documentées) ; `limit <= 0` ⇒ 400.

### Hors scope

- Export/impression PDF → task-190.
- Le contenu des logs → task-184 / task-341.
- Les `catch (Exception)` résiduels de `MailController` (task-066) et les retours hors ProblemDetails de
  `GetMailsByTagAsync` / `DraftController` → task-342 (AUD-66).
- Le retrait de `PurgeMailsResponseDto` de dtos-mss (voir ci-dessus).

## Definition of Done

- [ ] Build passes (0 errors) — `api-mail` et `client-blazor`
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test d'intégration : `DELETE /api/v1/maintenance/purge-mails` ⇒ **404**, et les tables mail sont
      **intactes** (ce test doit échouer sur le code actuel — le vérifier explicitement et consigner le run rouge)
- [ ] Aucune occurrence de `purge-mails` / `PurgeMailsAsync` dans `api-mail/src` ni `client-blazor/Src` (grep consigné)
- [ ] `client-blazor` : la page de gestion s'affiche sans le bouton de purge ; test bUnit de la page mis à jour (rendu sans bouton) ; aucune régression des autres actions de la page
- [ ] Test d'intégration : corps vide ou invalide sur **chacune** des actions listées au point 2 ⇒
      `400` `application/problem+json`, jamais `500` (dont `{"emailUid":""}` pour un type numérique)
- [ ] Test d'intégration : `GET /api/v1/settings/settings` ⇒ `405`, et les paramètres du praticien sont **inchangés**
- [ ] Test d'intégration : `list-emails?limit=-1` ⇒ `400` ; `limit` très grand ⇒ borné, réponse de taille maîtrisée
- [ ] Non-régression : les corps valides sont traités à l'identique sur toutes les actions listées
- [ ] Aucune fuite de détail technique dans les corps d'erreur (pas de trace d'exception, de chaîne de connexion ni de donnée de santé)

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost` ; Blazor : `cd Client/Blazor && dotnet run --project <projet Shell>`.
2. **Purge supprimée** : `curl -i -X DELETE https://localhost:{port}/api/v1/maintenance/purge-mails -H "Authorization: Bearer {jeton praticien}"`
   → **404**, la boîte est intacte. **Avant correctif : `200 {"success":true}` et la base mail est
   vidée** — ne tester le cas « avant » que sur une base jetable.
3. **Blazor** : ouvrir la page de gestion MSS → le bouton « Purger » n'existe plus ; les autres actions de la page fonctionnent.
4. **Corps invalide** : `curl -i -X POST .../api/v1/ai/improve-text -H "Content-Type: application/json" -d ''`
   → `400` problem+json (avant : `500`). Répéter avec
   `PUT .../api/v1/patients/{patientId}/opposition -d 'null'` (la route à INS dans le chemin n'existe
   plus depuis `754a194f`) et `POST .../api/v1/diagnostics/recalculate-summary -d '{"emailUid":""}'`.
5. **GET qui écrit** : noter les paramètres actuels du praticien, puis
   `curl -i -X GET .../api/v1/settings/settings -d '{...}'` → `405`, paramètres inchangés. Avant : écrasés.
6. **Pagination** : `curl -i ".../api/v1/maintenance/list-emails?limit=-1"` → `400` (avant : `500`) ;
   `?limit=100000000` → réponse bornée.
7. Non-régression : parcours nominal complet (lecture, envoi, paramètres, recherche, IA) inchangé.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : correctif de conformité — intégrité des données (suppression d'une purge destructive), robustesse de l'API et contrat d'erreur homogène (règle 12, RFC 7807)
- **INS** : non applicable — la route d'opposition à INS dans le chemin a déjà été retirée (`754a194f`)
- **Authentification PS** : inchangée (PSC / e-CPS)
- **Habilitations** : **cœur du point 1** — un endpoint destructif n'a pas sa place dans l'API ; sa suppression retire le besoin d'une habilitation dédiée
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : les appels à la route supprimée aboutissent en 404 (journal d'accès standard) ; aucune donnée de santé dans les corps d'erreur
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : **à vérifier avec l'humain** — l'endpoint de purge a-t-il été atteint sur un environnement réel ? Une perte de données de santé (art. 32 : disponibilité et intégrité) devrait être qualifiée ; les journaux d'accès à `DELETE /api/v1/maintenance/purge-mails` sont la source à contrôler
