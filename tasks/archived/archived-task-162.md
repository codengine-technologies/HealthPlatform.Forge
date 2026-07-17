# todo-task-162.md — Dashboard mobile : casser la boucle de rétroaction enrichissement → refresh (429 en cascade)

**Repos**: client-mobile, api-mail
**Dependencies**: wip-task-161
**Epic**: E012

> **Relation à task-161** — task-162 est le **complément root-cause** de task-161,
> pas son remplacement. task-161 a livré la garde de session (Problème 1) + le
> `debounceTime(400ms)` et le respect du `Retry-After` (atténuation du Problème 2).
> Le stack trace a prouvé que le debounce **cadençait** la boucle sans la casser :
> task-162 supprime la **source** de rétroaction (`emailsEnriched$ → refresh`). Le
> debounce de 161 reste en place comme filet défensif. Les deux touchent
> `home.page` + `dashboard-refresh` et doivent voyager ensemble jusqu'à `develop`.

## Objective

Éliminer la **boucle de rechargement auto-entretenue** de l'onglet **Accueil**
mobile (`/tabs/home`) qui sature le rate-limiter backend (HTTP 429 en cascade
sur tous les endpoints du dashboard). Diagnostic établi par test Playwright +
analyse Seq + stack trace console.

task-161 avait ajouté un `debounceTime(400ms)` sur le bus de refresh, mais ce
n'était que le **cadencement** d'une boucle qui reste alimentée à la source :
le fix ne cassait pas la boucle. Cette task s'attaque à la **cause racine**.

### Cause racine (prouvée par le stack trace)

`home.page` abonnait le rafraîchissement du dashboard au flux SSE
d'**enrichissement** :

```
EventSource "EmailsEnriched"
 → mail-events-stream.service.ts   emailsEnrichedSubject.next()
 → home.page.ts                    .subscribe(() => this.refresh.trigger())   ⟵ couplage fautif
 → dashboard-refresh.service.ts    refreshSubject.next()  (debounceTime 400ms — actif mais impuissant)
 → messaging-counters-widget       load() → forkJoin(getFolder, getFolderToday, getFolders)
 → GET /api/v1/mail/folders → 429
```

Deux mécanismes se renforçaient :

1. **Flux d'enrichissement continu** : sur une INBOX volumineuse (~6300 mails),
   le backend émet des `EmailsEnriched` en continu pendant des minutes.
   `debounceTime(400)` ne fait que cadencer les rechargements (~1 / 400 ms) sans
   les supprimer → dizaines de rechargements complets → saturation → 429.
2. **Rétroaction fermée** : chaque rechargement lit les dossiers
   (`getFolder`/`getFolders`), ce qui côté backend re-déclenche l'enrichissement
   → nouveaux `EmailsEnriched` → refresh → lecture des dossiers → … La boucle
   s'auto-entretient **indépendamment de la taille de la boîte**.

## Comportement attendu

1. **Découplage compteurs / enrichissement** : le dashboard ne se recharge plus
   sur les évènements d'enrichissement. L'enrichissement ajoute des tags/résumés
   IA à des mails déjà connus — il ne change aucun compteur (Aujourd'hui / Non
   lus / Total). Le refresh du dashboard n'est piloté que par : nouveau mail
   (`notification$`), retour d'onglet (`ionViewWillEnter`), pull-to-refresh.
2. **Lecture ≠ enrichissement (backend)** : une simple lecture de dossier
   (`GET /api/v1/mail/folders`, `.../folders/{folder}`) ne doit pas déclencher
   un cycle d'enrichissement susceptible de ré-émettre `EmailsEnriched`.
   Auditer et, le cas échéant, dissocier lecture et déclenchement d'enrichissement.
3. **Plus de boucle** : sur `/tabs/home` avec session valide et enrichissement
   en cours, aucune rafale de 429 ; le dashboard se stabilise.

## Definition of Done

- [ ] Build passes (`npm run build`, 0 errors) + (`dotnet build` api-mail si touché)
- [ ] Tests pass (`npm test -- --watch=false --browsers=ChromeHeadless`) + `dotnet test` api-mail si touché
- [ ] `home.page` ne s'abonne plus à `emailsEnriched$` pour déclencher `refresh.trigger()`
- [ ] Le refresh du dashboard n'est piloté que par `notification$` + retour d'onglet + pull-to-refresh
- [ ] Test unitaire `home.page` : un évènement `emailsEnriched$` ne déclenche AUCUN `refresh.trigger()`
- [ ] Test unitaire : un évènement `notification$` déclenche bien un `refresh.trigger()`
- [ ] Audit backend documenté : une lecture de dossier ne (re)déclenche pas d'enrichissement en boucle (sinon fix + test)
- [ ] Vérif manuelle : `/tabs/home` session valide, enrichissement en cours → 0 rafale de 429 (logs Seq `StatusCode = 429` sur la période)
- [ ] Aucune donnée de santé en clair dans les logs (INS, NIR, contenu CDA/MSSanté)

## Manual Test Plan

- Lancer le mobile : `cd Client/Mobile && npm start` (http://localhost:8100), backend `api-mail` + proxy PSC, session e-CPS valide
- Ouvrir l'onglet **Accueil** sur une boîte volumineuse (enrichissement actif)
- Attendu : les widgets se chargent une fois et se stabilisent ; **aucune** rafale de 429 dans les logs Seq ; la console ne défile pas en boucle de `GET /folders 429`
- Ouvrir un mail non enrichi puis revenir sur Accueil : l'enrichissement tourne en fond (inbox) mais NE recharge PAS le dashboard
- Recevoir un nouveau mail (ou simuler `notification$`) : le dashboard se rafraîchit bien (compteurs à jour)
- Pull-to-refresh : recharge une fois, se referme

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR spécifique — correctif de robustesse d'un écran existant (E012)
- **Exigences DSR honorées** : non applicable — robustesse d'un écran déjà référencé
- **INS** : non applicable — le dashboard n'affiche aucun trait INS, aucune manipulation d'identité patient
- **Authentification PS** : e-CPS / PSC (eIDAS substantiel) — inchangé
- **Habilitations** : non applicable — inchangé
- **Interop CI-SIS** : non applicable — aucun échange métier touché
- **Tracé PGSSI-S** : non applicable — aucun nouvel évènement métier ; les logs HTTP (dont 429) restent en place
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable — correctif front + audit backend, aucune donnée nouvelle stockée
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement de données

## Branches
- `client-mobile` (pushed) : `feat/task-162-break-enrichment-refresh-loop` — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-162-break-enrichment-refresh-loop

## Develop log (volet client-mobile — implémenté sur base staging, décision humaine)
- **Contexte** : suite de task-161 (même base staging `forge/staging-task-142-160`), root-cause du Problème 2.
- **Fix** : retrait de l'abonnement `emailsEnriched$ → refresh.trigger()` dans `home.page` (le refresh reste piloté
  par `notification$` + retour d'onglet + pull-to-refresh). Le `debounceTime(400ms)` de task-161 reste en filet.
- **Commit** : `77ab50a` (feat/task-162) — 2 fichiers (`home.page.ts`, `home.page.spec.ts`), test unitaire inversé.
- **Validation** : tests ✓ **738/0** (headless) ; vérif manuelle humaine `/tabs/home` session valide → boucle 429 **résolue**.
- **Agrégée sur la staging** : merge `2390232` (staging couvre 142→162).
- **PR vers `develop`** : **différée** — même gate de merge que le batch (task-149 #53) ; les commits de 161 + 162
  sont cherry-pickables ensemble sur une branche issue de `develop` une fois le batch mergé → PR propre + autonome.
- **Reste à faire (volet `api-mail`, non bloquant)** : audit « lecture de dossier ≠ déclenchement d'enrichissement »
  pour garantir qu'aucune rétroaction ne puisse réapparaître côté serveur.

## Merged
- 2026-07-17 — assemblée et mergée via PR #53 (grappe dashboard 149+161+162, merge atomique)
- `client-mobile` : 552a8ab (PR #53 fermée)
