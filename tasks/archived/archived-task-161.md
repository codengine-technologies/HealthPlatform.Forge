# todo-task-161.md — Dashboard mobile : robustesse au chargement (session expirée + tempête de refresh → 429)

**Repos**: client-mobile
**Dependencies**: done-task-149
**Epic**: E012

## Objective

Corriger deux défauts de robustesse de l'onglet **Accueil** mobile
(`/tabs/home`, `home.page` — task-149) mis en évidence par un test Playwright +
analyse des logs Seq. Défauts purement front (`client-mobile`) ; le backend et
son rate-limiter (`api-mail`, task-090) restent inchangés — ils fonctionnent
comme prévu, c'est le client qui les sollicite mal.

### Problème 1 — 6 erreurs JS non catchées quand la session est absente / expirée

À l'ouverture de `/tabs/home` sans session valide (déconnecté ou session
e-CPS expirée), les 5 widgets du dashboard se chargent dès `ngOnInit` sans
vérifier qu'une session existe. Chacun appelle `MssApiService`, dont le getter
`baseUrl` **jette une exception synchrone** (`MSS API URL is not configured.
Please login first.`, `mss-api.service.ts:903`). Le throw survient **pendant
l'évaluation des arguments de `forkJoin({...})`**, donc **avant** que le
handler `error:` du `subscribe` soit branché → l'exception échappe au handler
et remonte comme erreur non catchée (5 widgets = 5 erreurs, + 1 sur le refresh
token 401). L'app finit par rediriger vers `/login?expired=1`, mais l'écran
clignote et la console est polluée.

### Problème 2 — tempête de requêtes → HTTP 429 en session réelle

En session réelle, `home.page` réabonne le rafraîchissement à **chaque**
évènement SSE (`notification$` **et** `emailsEnriched$`, `home.page.ts:35-42`).
Chaque `refresh.trigger()` recharge **les 5 widgets en fan-out** (le seul widget
Messagerie = 3 requêtes en `forkJoin`). L'enrichissement (`enrich/sync`) émet
lui-même des évènements `emailsEnriched$`, qui redéclenchent un refresh → boucle
de rafraîchissement. Sur une boîte volumineuse (observé : ~6300 non-lus du
jour), et *a fortiori* avec le même PS connecté sur deux appareils (partition
rate-limit partagée `user:<sub>`), les 100 requêtes / 10 s du rate-limiter sont
dépassées → cascade de **429** sur `emails/unread/recent` et `emails/enrich/sync`.
Aucun debounce sur le bus refresh, et le `Retry-After` renvoyé par le backend
n'est pas respecté côté client.

## Comportement attendu

1. **Garde de session** : aucun widget du dashboard ne déclenche d'appel API
   tant qu'aucune session valide n'existe. En l'absence de session, l'écran
   n'émet aucune erreur console et laisse la redirection login se faire
   proprement.
2. **`baseUrl` non bloquant** : l'absence de session produit une erreur
   *observable* (`throwError`), attrapée par le handler `error:` des widgets
   (état d'erreur propre), jamais une exception synchrone non catchée.
3. **Coalescence des refresh** : les rafales d'évènements SSE (notamment
   l'auto-enrichissement) sont regroupées (debounce/audit) de sorte qu'un burst
   ne génère qu'**une** vague de rechargement des widgets.
4. **Respect du `Retry-After`** : sur réponse 429, le client n'émet pas de
   re-tir immédiat ; il applique le délai `Retry-After` renvoyé par le backend.

## Definition of Done

- [ ] Build passes (`npm run build`, 0 errors)
- [ ] Tests pass (`npm test -- --watch=false --browsers=ChromeHeadless`, 0 failures)
- [ ] Les widgets du dashboard ne déclenchent aucun appel API sans session valide (garde de session)
- [ ] `MssApiService.baseUrl` sans session → `Observable` en erreur (via `throwError`), plus de throw synchrone hors pipeline Rx
- [ ] Ouverture de `/tabs/home` déconnecté : **0 erreur console** liée à « MSS API URL is not configured »
- [ ] Bus `DashboardRefreshService.refresh$` : debounce/audit des rafales, une seule vague de rechargement par burst SSE (test unitaire avec `fakeAsync`/`TestScheduler`)
- [ ] Sur 429, le client respecte l'en-tête `Retry-After` (pas de re-tir immédiat) — test unitaire sur l'intercepteur / la stratégie de retry
- [ ] Test unitaire : widget en état « pas de session » → rend l'état neutre/erreur sans lever
- [ ] Aucune donnée de santé en clair dans les logs (INS, NIR, contenu CDA/MSSanté)
- [ ] Authentification PS via e-CPS/PSC : le cas « session expirée » redirige proprement vers `/login?expired=1`

## Manual Test Plan

- Lancer le mobile : `cd Client/Mobile && npm start` (http://localhost:8100)
- Lancer le backend `api-mail` + le proxy PSC habituels (session e-CPS valide requise pour le cas nominal)

**Cas 1 — déconnecté (Problème 1)**
- Sans session (ou vider le storage de session), ouvrir http://localhost:8100/tabs/home
- Attendu : redirection vers `/login?expired=1`, **aucune** erreur console « MSS API URL is not configured »

**Cas 2 — session réelle, pas de tempête 429 (Problème 2)**
- Se connecter via e-CPS, ouvrir l'onglet **Accueil** sur une boîte volumineuse
- Laisser l'enrichissement tourner, revenir/quitter l'onglet plusieurs fois, pull-to-refresh
- Attendu : les widgets se chargent, **aucun 429** en rafale dans les logs Seq (`StatusCode = 429` filtré sur la période), un burst SSE ne provoque qu'une vague de rechargement
- Bonus : ouvrir la même session sur deux appareils (ou deux onglets) → toujours pas de 429 en usage normal

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR spécifique — correctif de robustesse d'un écran existant (E012)
- **Exigences DSR honorées** : non applicable — aucune nouvelle exigence, robustesse d'un écran déjà référencé
- **INS** : non applicable — le dashboard n'affiche pas de trait INS, aucune manipulation d'identité patient dans le scope
- **Authentification PS** : e-CPS / PSC (niveau eIDAS substantiel) — inchangé ; la correction améliore la gestion de la **session expirée** (redirection propre vers login)
- **Habilitations** : non applicable — inchangé
- **Interop CI-SIS** : non applicable — aucun échange métier (CDA/FHIR/HL7v2) touché
- **Tracé PGSSI-S** : non applicable — aucun nouvel évènement métier ; les logs HTTP existants (dont 429) restent en place
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable — correctif front, aucune donnée nouvelle stockée/traitée
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement de données

## Branches
- `client-mobile` (pushed) : feat/task-161-home-load-robustness — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-161-home-load-robustness

## Develop log (implémentation sur base staging — décision humaine)
- **Contexte** : task-161 cible le dashboard de task-149, absent de `develop` (PR #53 non mergée).
  Sur demande humaine, implémentée sur `feat/task-161-home-load-robustness` **basée sur la
  staging** `forge/staging-task-142-160-20260716` (qui contient 142→160), puis agrégée sur la staging.
- **Fix 1 (session)** : `DashboardRefreshService.hasSession` (garde partagée) + guard en tête du
  `load()` des 5 widgets (état neutre, aucun appel API sans session) ; `MssApiService` — 12 méthodes
  du dashboard enveloppées dans `defer(...)` → le throw de `baseUrl` devient une erreur Rx attrapée
  par `error:` (fin des exceptions synchrones non catchées échappant `forkJoin`).
- **Fix 2 (429)** : `refresh$` débouncé (`REFRESH_DEBOUNCE_MS=400`) → une vague par rafale SSE ;
  interceptor respecte `Retry-After` sur 429 (1 rejeu via `timer`, token `RATE_LIMIT_RETRIED`,
  helper pur `parseRetryAfterMs`). 401/refresh inchangé.
- **Commits** (feat/task-161) : f90f5ec, 29277ee, 3919310 (+ capture 2496754).
- **Validation** : build ✓ 0 erreur, **tests ✓ 738/0** (+15 vs 723), lint ✓ 0 erreur, code review APPROVED,
  vérif visuelle `/tabs/home` ✓ (5 widgets, non-blank, 0 erreur console).
- **Agrégée sur la staging** : commit 54dce54 (staging couvre 142→161).
- **PR vers `develop`** : **différée** — impossible tant que le batch (dont task-149/#53) n'est pas
  mergé (une PR depuis cette branche embarquerait tout le batch). Les 3 commits de fix sont
  cherry-pickables sur une branche issue de `develop` une fois le batch mergé → PR propre + autonome.
- **DOD live** : le check console navigateur déconnecté (Cas 1 du Manual Test Plan) reste à la
  charge humaine (app + proxy PSC en local) — couvert par tests unitaires côté forge.

## Merged
- 2026-07-17 — assemblée et mergée via PR #53 (grappe dashboard 149+161+162, merge atomique)
- `client-mobile` : 552a8ab (PR #53 fermée)
