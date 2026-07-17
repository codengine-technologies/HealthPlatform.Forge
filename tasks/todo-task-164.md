# todo-task-164.md — Création de groupe de contacts : NullReferenceException sur corps null

**Repos**: api-mail, client-mobile

## Objective

Corriger le crash **500 `NullReferenceException`** à la création d'un groupe de
contacts MSSanté, reproduit depuis l'application mobile. Le contrôleur
déréférence le corps de requête sans garde : quand `[FromBody] ContactGroupDto
group` est lié à `null` (corps vide, JSON `null`, ou `Content-Type` inattendu),
`group.Name` lève une `NullReferenceException` non gérée → 500.

Deux volets :
1. **Backend (`api-mail`) — robustesse** : ne jamais transformer un corps
   invalide en 500 ; renvoyer un **400 `ProblemDetails`** (RFC 7807, règle 12).
2. **Mobile (`client-mobile`) — investigation** : comprendre pourquoi le POST
   `createGroup` arrive avec un corps lié à `null` côté backend, et corriger le
   payload si nécessaire.

### Cause racine (identifiée)

[ContactController.cs:274](../../Api/Mail/src/Api/Controllers/V1/ContactController.cs#L274) :

```csharp
public async Task<IActionResult> CreateGroupAsync([FromBody] ContactGroupDto group, ...)
{
    ...
    logger.LogInformation("➕ CreateGroup - Name={Name}", group.Name);  // ⟵ NRE si group == null
    if (!ModelState.IsValid) return BadRequest(ModelState);              // check APRÈS le déréférencement
    ...
}
```

- `group` est déréférencé (`group.Name`) **avant** toute validation.
- Le check `ModelState.IsValid` vient trop tard, et `[ApiController]` n'a pas
  intercepté ce cas (corps `null`/vide qui contourne la validation auto de body).
- **Même défaut latent** dans `UpdateGroupAsync`
  ([ContactController.cs:292](../../Api/Mail/src/Api/Controllers/V1/ContactController.cs#L292)) qui log aussi `group.Name` avant la validation.

Trace : `ContactController.CreateGroupAsync` → `group.Name` → `NullReferenceException` → 500.

### Preuve Seq (2026-07-17)

- **2 occurrences** : `09:44:46` puis `09:45:20` (retry du PS ~34 s après), user
  `robert.specialiste…@medecin.formation.mssante.fr`, **iPhone / app mobile**
  (`ClientSessionId n2ngms5T23n8dNv-a-Xcifoh`), `POST /api/v1/Contact/groups`.
- `System.NullReferenceException` à `ContactController.cs:line 274`.
- **Déjà routée par le `GlobalExceptionHandler`** (`SourceContext =
  mss.mail.api.ErrorHandling.GlobalExceptionHandler`) → le client reçoit un
  `ProblemDetails` **500**. L'infra RFC 7807 (règle 12) fonctionne : le correctif
  n'est PAS d'ajouter un `try/catch`, mais de **garder `group == null` tôt** pour
  transformer ce 500 en **400** et supprimer la NRE.
- Le `[ApiController]` n'a pas produit le 400 auto (corps `null`/vide qui
  contourne la validation de body) → garde explicite nécessaire.
- Le payload n'est pas journalisé → volet mobile : identifier pourquoi le corps
  arrive lié à `null`.

Le mobile envoie pourtant un objet via
[mss-api.service.ts:441](../../Client/Mobile/src/app/core/services/mss-api.service.ts#L441)
(`POST /api/v1/Contact/groups`, body `group`) — d'où le volet investigation :
le payload est-il `undefined`/mal formé au moment de l'appel, ou un champ le fait-il
désérialiser à `null` côté backend ?

## Comportement attendu

1. **Backend jamais en 500 sur corps invalide** : un corps `null`/vide/illisible
   sur `POST` et `PUT /groups` renvoie **400 `ProblemDetails`** (title/detail/status),
   jamais une `NullReferenceException`. La garde précède tout déréférencement et
   tout log.
2. **Création nominale inchangée** : un `ContactGroupDto` valide crée le groupe
   (201/200) comme aujourd'hui.
3. **Mobile** : la création de groupe depuis l'app envoie un corps valide et
   réussit ; si un payload `null`/mal formé était émis, il est corrigé.

## Definition of Done

- [ ] Build passe (`dotnet build HealthPlatform.Api.Mail.sln`) — 0 erreur ; `npm run build` mobile si touché — 0 erreur
- [ ] Tests passent (`dotnet test HealthPlatform.Api.Mail.sln`) ; `npm test -- --watch=false --browsers=ChromeHeadless` mobile si touché
- [ ] `CreateGroupAsync` : garde `group == null` (et `ModelState` invalide) **avant** tout déréférencement/log → 400 `ProblemDetails` (règle 12), plus de NRE
- [ ] `UpdateGroupAsync` : même garde appliquée (défaut latent corrigé)
- [ ] Test d'intégration `POST /api/v1/Contact/groups` : corps `null`/vide → **400** `application/problem+json` (pas 500)
- [ ] Test d'intégration `POST /api/v1/Contact/groups` : corps valide → 200/201, groupe créé (happy path)
- [ ] Mobile : cause du corps `null` identifiée ; création de groupe testée bout-en-bout (ou note explicite si le défaut était 100 % backend)
- [ ] Aucune donnée sensible en clair dans les logs ; erreur en `ProblemDetails` corrélée par `traceId`

## Manual Test Plan

- Lancer `api-mail` : `cd Api/Mail && dotnet run` (+ mobile `cd Client/Mobile && npm start`, session e-CPS valide)
- **Nominal** : depuis l'app mobile, onglet Contacts → créer un groupe avec un nom → le groupe apparaît dans la liste, pas d'erreur
- **Robustesse backend** : envoyer un `POST /api/v1/Contact/groups` avec un corps vide → réponse **400 `problem+json`** (« corps requis / invalide »), **pas** de 500
- Vérifier les logs Seq : plus de `NullReferenceException` sur `ContactController.CreateGroupAsync`

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : socle MSSanté (carnet de contacts) — correctif de robustesse, pas de nouvelle exigence DSR
- **Exigences DSR honorées** : non applicable — fiabilisation d'un endpoint existant
- **INS** : non applicable — groupe de **contacts professionnels**, aucune donnée patient ni INS
- **Authentification PS** : e-CPS / PSC — inchangée
- **Habilitations** : inchangées (création de groupe déjà autorisée)
- **Interop CI-SIS** : non applicable — DTO propriétaire `ContactGroupDto`, aucun échange CDA/FHIR
- **Tracé PGSSI-S** : la création de groupe reste journalisée (canal existant) ; l'erreur sort corrélée `traceId`
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable — donnée de contacts, pas de DSCP patient
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement
