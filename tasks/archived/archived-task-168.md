# todo-task-168.md — Création contact/groupe mobile : `id:""` invalide pour un Guid → binding null → NRE

**Repos**: client-mobile

## Objective

Corriger l'échec de **création de contact et de groupe** MSSanté depuis l'app
mobile. Le mobile envoie `"id":""` (chaîne vide) pour une entité neuve ; le
backend type `ContactDto.Id` / `ContactGroupDto.Id` en **`Guid` non-nullable** ;
System.Text.Json ne peut pas désérialiser `""` en `Guid` → l'échec de binding lie
tout le `[FromBody]` à **`null`**. Comme `api-mail` a
`SuppressModelStateInvalidFilter = true`, aucun 400 auto n'est renvoyé →
l'action tourne avec le DTO `null` → **NRE 500** (ou 400 « corps requis »
trompeur si la garde task-164 est là).

Fix : **ne jamais envoyer `id:""` en création** — omettre `id` (le backend
génère un Guid v7). Édition (id réel présent) inchangée.

## Cause racine (PROUVÉE — capture réseau + Seq + curl direct, 2026-07-17)

- Payload mobile capturé : `{"id":"","type":0,"firstName":"AGATHE",…}` — JSON
  valide, `Content-Length: 356`, envoyé sur le fil.
- `Dtos/ContactDto.cs` : `public Guid Id { get; set; }` (non-nullable). `""` →
  Guid = échec de désérialisation STJ.
- `Program.cs` : `.ConfigureApiBehaviorOptions(o => o.SuppressModelStateInvalidFilter = true)`
  → pas de 400 auto sur binding invalide → action exécutée avec `contact = null`.
- **Preuve curl direct au backend `http://localhost:5052` (bypass proxy), même token** :
  - body **avec `"id":""`** → **HTTP 500** (NRE `ContactController.cs:107`) ;
  - body **sans `id`** → **HTTP 200** en 0,36 s, Guid v7 généré par le backend.

### Pistes ÉCARTÉES (ne pas refaire)
Proxy dev Vite/`http-proxy` (curl direct échoue pareil) · corps perdu en transit ·
HTTPS/HTTP-2 · refresh-replay de l'intercepteur (aucun `/auth/refresh` dans la
trace) · middleware backend consommant le body (aucun `Request.Body` dans src/Api).
Le « stall » multi-secondes observé = leurre (warmup validation JWT/JWKS), pas la cause.

## Comportement attendu

1. Création de contact et de groupe depuis l'app → **201/200**, l'entité apparaît,
   sans erreur (le backend assigne le Guid).
2. Le payload de création **n'inclut pas `id`** (ni `""`, ni `null`) — la propriété
   est absente.
3. Édition (id réel) inchangée : `id` conservé, `PUT` fonctionne.

## Definition of Done

- [ ] `npm run build` — 0 erreur
- [ ] `npm test -- --watch=false --browsers=ChromeHeadless` — 0 échec
- [ ] `toContactDto` : en création (`form.id` vide) le payload **omet `id`** ; en édition l'`id` est conservé — test unitaire (`'id' in dto` false en création, présent en édition)
- [ ] `createGroup` : le payload de création **omet `id`** (plus de `id:''`)
- [ ] Vérif manuelle : créer un contact **et** un groupe dans l'app → 201/200, apparaissent ; Seq sans NRE `ContactController`
- [ ] Rollback du faux fix proxy (`proxy.conf.json` rétabli sur `https://localhost:7012`) — fait
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- `cd Client/Mobile && npm start` (branche feat/task-168), backend + proxy PSC, session e-CPS valide
- Onglet **Contacts** → créer un contact avec une adresse MSSanté → **apparaît** (201), pas d'erreur
- Créer un **groupe** → apparaît (200/201)
- Éditer un contact existant → **PUT** OK (id conservé)
- Seq : `POST /api/v1/Contact` et `/Contact/groups` en 2xx, plus de `NullReferenceException`

## Note transverse (hors scope, à considérer)
`SuppressModelStateInvalidFilter = true` (task-055) **masque les erreurs de
binding en 500** (NRE) au lieu d'un 400 `ProblemDetails` propre. Un payload
invalide (ex. `id:""`) devrait sortir en 400 explicite. À arbitrer séparément
(impacte tous les controllers). task-164 (`RequireBody`) atténue en surface mais
ne couvre pas les échecs de binding partiels.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : socle MSSanté (carnet de contacts) — correctif client, pas de nouvelle exigence DSR
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — contacts professionnels
- **Authentification PS** : e-CPS / PSC — inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — DTOs propriétaires
- **Tracé PGSSI-S** : non applicable
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable — fix client
- **AIPD / impact RGPD** : inchangé

## Branches
- `client-mobile` (pushed) : feat/task-168-dev-proxy-body-forward — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-168-dev-proxy-body-forward
  (nom de branche hérité de la 1re hypothèse proxy, désormais abandonnée ; le fix réel est l'omission de `id`)

## PRs
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/59 — label `awaiting-human-merge`

## Develop log
- 2026-07-17 — cause racine prouvée (curl direct : body sans `id` → 201 ; avec `id:""` → 500). Fix = omission de `id` en création (`toContactDto` + `createGroup`, commit 1). Rollback proxy.
- Réparation collatérale (commit 2) : specs cassés par les union-merges du batch (imports dupliqués, blocs `it()` non fermés, `to:`→`toEmails`) → `npm test` recompile. **744 tests verts**, build ✓, hook ✓.
- À valider en live (création contact/groupe → 201). PR #59 en attente merge humain (HAG).

## Merged
- 2026-07-17 — squash-merge sur `develop` (`--i-tested`)
- `client-mobile` : 502cbad (PR #59 fermée) — fix id:"" (3 chemins) + réparation specs du batch
