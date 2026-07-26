# todo-task-164.md — ContactController : NullReferenceException sur corps `[FromBody]` null (contacts + groupes)

**Repos**: api-mail, client-mobile

## Objective

Corriger le crash **500 `NullReferenceException`** de plusieurs actions du
`ContactController` MSSanté, reproduit depuis l'application mobile. Chaque action
déréférence le corps de requête **sans garde** : quand le `[FromBody]` DTO est
lié à `null` (corps vide, JSON `null`, ou `Content-Type` inattendu), le premier
log/accès de champ lève une `NullReferenceException` non gérée → 500.

Défaut identique sur **4 actions** :

| Action | Ligne | Déréférencement fautif |
|---|---|---|
| `CreateAsync` (contact) | [107](../../Api/Mail/src/Api/Controllers/V1/ContactController.cs#L107) | `contact.DisplayName, contact.Type` |
| `UpdateAsync` (contact) | [125](../../Api/Mail/src/Api/Controllers/V1/ContactController.cs#L125) | `contact.DisplayName` |
| `CreateGroupAsync` (groupe) | [274](../../Api/Mail/src/Api/Controllers/V1/ContactController.cs#L274) | `group.Name` |
| `UpdateGroupAsync` (groupe) | [292](../../Api/Mail/src/Api/Controllers/V1/ContactController.cs#L292) | `group.Name` |

Deux volets :
1. **Backend (`api-mail`) — robustesse** : ne jamais transformer un corps
   invalide en 500 ; renvoyer un **400 `ProblemDetails`** (RFC 7807, règle 12).
2. **Mobile (`client-mobile`) — investigation** : comprendre pourquoi un POST/PUT
   contact/groupe arrive avec un corps lié à `null` côté backend, et corriger le
   payload si nécessaire.

### Cause racine (identifiée)

Motif commun aux 4 actions (exemple `CreateAsync`) :

```csharp
public async Task<IActionResult> CreateAsync([FromBody] ContactDto contact, ...)
{
    ...
    logger.LogInformation("➕ Create contact - Name={DisplayName}, Type={Type}",
        contact.DisplayName, contact.Type);   // ⟵ NRE si contact == null
    if (!ModelState.IsValid) return BadRequest(ModelState);  // check APRÈS le déréférencement
    ...
}
```

- Le DTO est déréférencé (log de ses champs) **avant** toute validation.
- Le check `ModelState.IsValid` vient trop tard, et `[ApiController]` n'a pas
  intercepté ce cas (corps `null`/vide qui contourne la validation auto de body).

Trace observée : `ContactController.CreateAsync` → `contact.DisplayName` →
`NullReferenceException` → 500 (ligne 107). Idem `CreateGroupAsync` (ligne 274,
cf. preuve Seq ci-dessous).

### Preuve Seq (2026-07-17, sur `CreateGroupAsync`)

- **2 occurrences** : `09:44:46` puis `09:45:20` (retry du PS ~34 s après), user
  `robert.specialiste…@medecin.formation.mssante.fr`, **iPhone / app mobile**
  (`ClientSessionId n2ngms5T23n8dNv-a-Xcifoh`), `POST /api/v1/Contact/groups`.
- `System.NullReferenceException` à `ContactController.cs:line 274`.
- **Déjà routée par le `GlobalExceptionHandler`** → le client reçoit un
  `ProblemDetails` **500**. L'infra RFC 7807 (règle 12) fonctionne : le correctif
  n'est PAS d'ajouter un `try/catch`, mais de **garder le DTO `== null` tôt** pour
  transformer ce 500 en **400** et supprimer la NRE.
- `CreateAsync` (contact, ligne 107) reproduit le même 500 (constaté en test manuel humain 2026-07-17).
- Le payload n'est pas journalisé → volet mobile : identifier pourquoi le corps
  arrive lié à `null` (setter `createContact`/`createGroup` : payload `undefined`/mal formé ?).

## Comportement attendu

1. **Backend jamais en 500 sur corps invalide** : un corps `null`/vide/illisible
   sur `POST`/`PUT` de `/api/v1/Contact` **et** `/api/v1/Contact/groups` renvoie
   **400 `ProblemDetails`**, jamais une `NullReferenceException`. La garde précède
   tout déréférencement et tout log, sur les **4 actions**.
2. **Nominal inchangé** : un `ContactDto`/`ContactGroupDto` valide crée/met à jour
   (200/201) comme aujourd'hui.
3. **Mobile** : création/màj de contact et de groupe envoient un corps valide et
   réussissent ; si un payload `null`/mal formé était émis, il est corrigé.

## Definition of Done

- [ ] Build passe (`dotnet build HealthPlatform.Api.Mail.sln`) — 0 erreur ; `npm run build` mobile si touché
- [ ] Tests passent (`dotnet test HealthPlatform.Api.Mail.sln`) ; `npm test -- --watch=false --browsers=ChromeHeadless` mobile si touché
- [ ] Les **4 actions** (`CreateAsync`, `UpdateAsync`, `CreateGroupAsync`, `UpdateGroupAsync`) gardent le DTO `== null` (et `ModelState` invalide) **avant** tout déréférencement/log → 400 `ProblemDetails` (règle 12), plus de NRE
- [ ] Facto : extraire un garde commun (helper / filtre) plutôt que dupliquer 4× (au choix de l'implémentation, sans sur-ingénierie)
- [ ] Test d'intégration `POST /api/v1/Contact` : corps `null`/vide → **400** `application/problem+json` (pas 500)
- [ ] Test d'intégration `POST /api/v1/Contact/groups` : corps `null`/vide → **400** (pas 500)
- [ ] Tests happy-path conservés (contact + groupe créés sur corps valide)
- [ ] Mobile : cause du corps `null` identifiée (contact + groupe) ; testé bout-en-bout (ou note si défaut 100 % backend)
- [ ] Aucune donnée sensible en clair dans les logs ; erreur en `ProblemDetails` corrélée par `traceId`

## Manual Test Plan

- Lancer `api-mail` : `cd Api/Mail && dotnet run` (+ mobile `cd Client/Mobile && npm start`, session e-CPS valide)
- **Nominal** : onglet Contacts → créer un contact, puis créer un groupe → apparaissent dans la liste, pas d'erreur
- **Robustesse backend** : `POST /api/v1/Contact` et `POST /api/v1/Contact/groups` avec un corps vide → **400 `problem+json`** (« corps requis / invalide »), **pas** de 500 ; idem `PUT` sur chacun
- Vérifier les logs Seq : plus de `NullReferenceException` sur `ContactController.CreateAsync`/`CreateGroupAsync`

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : socle MSSanté (carnet de contacts) — correctif de robustesse, pas de nouvelle exigence DSR
- **Exigences DSR honorées** : non applicable — fiabilisation d'endpoints existants
- **INS** : non applicable — **contacts professionnels**, aucune donnée patient ni INS
- **Authentification PS** : e-CPS / PSC — inchangée
- **Habilitations** : inchangées (création/màj contact & groupe déjà autorisées)
- **Interop CI-SIS** : non applicable — DTOs propriétaires `ContactDto`/`ContactGroupDto`, aucun échange CDA/FHIR
- **Tracé PGSSI-S** : les mutations restent journalisées (canal existant) ; l'erreur sort corrélée `traceId`
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable — donnée de contacts, pas de DSCP patient
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement

## Branches
- `api-mail` (pushed) : feat/task-164-contact-null-body-guard — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-164-contact-null-body-guard
- `client-mobile` (pushed) : feat/task-164-contact-null-body-guard — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-164-contact-null-body-guard
- `dtos-mss` (pushed, auto-inclus) : feat/task-164-contact-null-body-guard — sans commit attendu (aucun changement de contrat) → pas de PR

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/116 — label `awaiting-human-merge`
- `client-mobile` : aucun changement (mobile envoie toujours un corps valide) → branche supprimée, pas de PR
- `dtos-mss` : aucun changement → branche supprimée, pas de PR

## Develop log
- 2026-07-17 — garde commune `RequireBody(...)` sur les 4 actions ContactController → 400 ProblemDetails. Commit `7b8b5c6` (api-mail).
- Build ✓ 0/0 ; 38 tests ContactController ✓ (dont 4 null-body) ; hook ✓.
- Volet mobile : investigation initiale « aucun changement » **FALSIFIÉE** puis **cause racine trouvée** (2026-07-17). Preuve capture réseau + Seq : le navigateur envoie bien un corps valide (356 B), mais le **proxy dev `webpack-dev-server` (`/api → https://localhost:7012`) ne transmet pas le corps des POST/PUT** au backend → stall 3–16 s → bind `null`. Ni refresh (aucun `/auth/refresh` dans la trace), ni backend, ni caller. → **suivi dans [task-168]** (dev proxy body forwarding). **Dev-only** (prod = Capacitor direct).
- task-164 (garde `RequireBody` → 400) **reste valide** : defense-in-depth (mauvais corps = 400 propre, plus de NRE 500). Ne résout PAS à lui seul la création de contact. PR #116 en attente merge humain (HAG).

## Merged
- 2026-07-17 — squash-merge sur `develop` (`--i-tested`)
- `api-mail` : 82a714d (PR #116 fermée)
