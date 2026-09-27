# todo-task-328.md — L'assistant IA ne livre jamais à un médecin l'action préparée pour un autre : chaque conversation a son propre contexte d'exécution

**Repos**: api-mail
**Dependencies**: — (aucune)
**Epic**: E009
**Single frontend**: true
**Priorité**: **1** — fuite de données de santé entre praticiens : le médecin A peut recevoir le **nom et le téléphone d'un patient du médecin B**, ou un brouillon rédigé d'après les mails de B.

> **Origine.** Audit de détection de bugs du 2026-09-27
> (`Docs/audits/api-mail-audit-bugs-20260927.md`, **AUD-04**, contre-vérifié ligne à ligne).

## Ce qui est établi (develop @ `14d58398`)

- `src/Api/Extensions/SemanticKernelExtensions.cs:81, 133` : le `Kernel` est **Singleton**.
- `src/Application/Services/Implementation/AiConversationService.cs` (Scoped,
  `Api/DependencyInjection.cs:134`) :
  - `:29` `private readonly AiActionFunctionFilter _actionFilter = new();` — une instance par requête ;
  - `:79-87` : `if (!_kernel.Plugins.Contains("EmailActionsPlugin")) AddFromType<…>()` puis
    `if (!_kernel.FunctionInvocationFilters.Contains(_actionFilter)) _kernel.FunctionInvocationFilters.Add(_actionFilter);`
    — `Contains` compare **par référence**, donc toujours faux : chaque requête **ajoute un filtre
    au Kernel partagé**, jamais retiré ;
  - `:216-222` : la requête lit `_actionFilter.LastAction`.
- `src/Application/Filters/AiActionFunctionFilter.cs` : à **chaque** appel de fonction, **chaque**
  filtre enregistré écrit `_lastAction`.

**Scénario** : B demande « appelle le patient » → le modèle de B appelle `call_patient(phoneNumber,
patientName)` → tous les filtres écrivent l'action → A, dont le flux se termine au même moment sur le
même pod, lit son filtre et reçoit l'événement SSE `Action` de B. Idem `compose_email`,
`contact_practitioner`.

**Effets secondaires** : liste de filtres qui grossit sans fin (fuite mémoire, chaque prompt de
tagging/résumé traverse N filtres) ; mutation concurrente non protégée d'une collection lue par
d'autres requêtes ; au premier appel concurrent sur un pod neuf, `AddFromType` en double lève
`ArgumentException` → 500.

## Objective

Que l'action produite par une fonction de l'assistant ne soit **visible que de la conversation qui l'a
déclenchée**, et que le Kernel partagé ne soit plus jamais modifié par une requête.

### Périmètre

1. Aucune mutation du Kernel singleton pendant une requête : plugin et filtre enregistrés **une fois**
   à la composition, ou **clone** du Kernel par requête (`kernel.Clone()`) portant plugin et filtre —
   choix de `/develop` après lecture du code, justifié dans le task file.
2. L'action capturée est portée par un état **propre à l'invocation** (arguments de l'invocation,
   état de requête), jamais par un champ partagé.
3. Tous les autres consommateurs du Kernel (tagging, résumé, rédaction, recherche) inchangés dans leur comportement.

### Hors périmètre

- Le stockage des conversations en mémoire d'un seul pod (task-336).
- Le comptage des tokens (task-342).

## Definition of Done

- [ ] Build passes (0 errors) — `cd Api/Mail && dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] **Test rouge d'abord** (log du run rouge dans le task file) : deux `AiConversationService` construits sur le
      **même** Kernel ; la fonction invoquée pour la conversation B produit une action ; sur le code actuel la
      conversation A lit l'action de B ; après correctif A ne lit **rien**
- [ ] Test : N requêtes successives → le nombre de filtres du Kernel partagé est **constant**
- [ ] Test : deux premières requêtes concurrentes sur un Kernel neuf → aucune `ArgumentException`
- [ ] Test : l'action d'une conversation lui revient bien (chemin nominal `call_patient`, `compose_email`, `contact_practitioner`)
- [ ] Non-régression : tests existants du tagging, du résumé et de la rédaction verts
- [ ] Aucun nom, téléphone ni contenu de mail ajouté dans les logs

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost` ; deux comptes praticiens de test (A et B) sur deux navigateurs.
2. B ouvre l'assistant et demande « appelle le patient » sur un mail de test porteur d'un patient fictif.
3. Au même moment, A pose une question quelconque à l'assistant.
4. **Attendu** : A ne reçoit **aucune** proposition d'action ; B reçoit la sienne. Avant correctif : A peut recevoir la proposition d'appel du patient de B.
5. Répéter une vingtaine de fois : la mémoire du processus API reste stable (pas de croissance liée au nombre de conversations).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif de confidentialité
- **Exigences DSR honorées** : non applicable — rétablit le cloisonnement entre praticiens (PGSSI-S)
- **INS** : non applicable — mais la US empêche la fuite de traits d'identité patient (nom, téléphone) entre praticiens
- **Authentification PS** : inchangée (PSC / e-CPS)
- **Habilitations** : **au cœur** — une donnée patient d'un praticien ne doit jamais atteindre un autre praticien
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé ; aucune donnée patient ajoutée aux logs
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : à informer le DPO — fuite potentielle entre praticiens avant correctif ; traitement inchangé après
