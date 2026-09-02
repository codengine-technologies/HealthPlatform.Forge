# todo-task-289.md — Un feature flag absent de l'environnement Flagsmith désactive silencieusement l'étage IA de toute l'application

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015
**Single frontend**: true

> **Origine** : incident **observé en exécution réelle** sur le déploiement
> Staging (Kubernetes, namespace `healthplatform`) le **2026-09-02 à 17:44**,
> pas déduit d'une lecture de code — voir « Preuve ».
>
> Cette US est la suite directe de `task-199` (évaluation locale + repli
> déclaré par flag) et de `task-201` (snapshot partagé Redis). Toutes deux
> couvraient le cas **« Flagsmith injoignable »**. Le cas
> **« Flagsmith joignable mais incomplet »** n'était pas couvert — c'est
> précisément celui qui s'est produit.

## Objective

Garantir qu'un feature flag déclaré par l'application mais **absent de
l'environnement Flagsmith** dégrade **ce flag seul**, et jamais l'état des
autres flags. Et rendre cet écart **visible dès le démarrage**, au lieu de le
laisser se manifester des heures plus tard par la disparition inexpliquée
d'une fonctionnalité médicale.

Aujourd'hui, le rafraîchissement du snapshot évalue les onze flags de
`FeatureFlags.All` dans une seule boucle. Le client Flagsmith **lève** sur un
flag inconnu de l'environnement ; comme l'appel est dans la boucle, la
première absence avorte le rafraîchissement **entier**. Aucun snapshot n'est
jamais publié, donc les onze flags retombent sur leur repli de démarrage à
froid. Or ce repli n'est pas neutre : les widgets de tableau de bord sont en
fail-open (`true`), mais les flags `ai_*` sont en fail-closed (`false`).

**Conséquence médicale mesurée** : parce que huit flags de widgets créés par
`task-274` n'existaient pas dans l'environnement Staging, l'étage IA de la
pipeline d'enrichissement était éteint pour **tous** les praticiens, et
**chaque** demande de résumé d'un mail clinique répondait « résumé non
disponible ». Le praticien ne voit aucune erreur : il voit une fonctionnalité
absente.

**US backend-only (justification)** : mécanique interne d'évaluation de flags
côté serveur. Aucun contrat d'API, aucun DTO et aucun écran ne changent — le
comportement observable côté frontends est le **retour** du comportement
nominal, pas un comportement nouveau.

### Preuve (logs des réplicas api-mail, Staging, 2026-09-02)

Le warning de `task-199` (un log par fenêtre, pas une stack par évaluation)
nomme le flag fautif :

```
17:44:16 [WRN] [FeatureFlag] Flagsmith refresh failed (3 failure(s) since last report)
                — serving last known flag state
Flagsmith.FlagsmithClientError: Feature does not exist: dashboard_widget_mail_counters
   at Flagsmith.Flags.GetFlag(String featureName)
   at Flagsmith.Flags.IsFeatureEnabled(String featureName)
   at mss.mail.api.Extensions.FlagsmithFeatureFlagService.RefreshAsync()
```

Et, dans la même seconde, la conséquence sur le chemin métier — répétée pour
chaque UID demandé par le praticien (`4816`, `4821`, `4825`, `4826`, `4890`, …) :

```
17:44:16 [WRN] ⚠️ Handled 404 - GET /api/v1/mail/folders/INBOX/emails/summary/4821
mss.mail.application.Exceptions.NotFoundException: AI summary is not available.
   at mss.mail.api.Controllers.V1.MailController.GetEmailSummaryAsync(...)
```

Deux faits qui établissent la chaîne de causalité, et non une simple
corrélation :

1. **Le message « serving last known flag state » est trompeur** : aucun état
   n'a jamais été connu. `_snapshot` n'est jamais affecté puisque
   l'affectation suit la boucle qui lève. Ce sont donc les replis de démarrage
   à froid qui s'appliquent, pas un dernier état connu.
2. **Les flags `ai_*` sont en tête de `FeatureFlags.All`** : leurs valeurs
   avaient déjà été lues **avec succès** auprès de Flagsmith avant que la
   boucle ne lève sur le premier flag de widget. Elles sont jetées avec le
   reste. L'étage IA est donc éteint par un flag **sans aucun rapport avec
   lui**.

Fichiers concernés (localisation du défaut, à titre de repère — l'implémentation
reste le choix de `/develop`) :

- `Api/Mail/src/Api/Extensions/FlagsmithFeatureFlagService.cs` — `RefreshAsync()`,
  la boucle sur `FeatureFlags.All` ; même motif à re-vérifier sur le chemin
  d'identité praticien introduit par `task-274`.
- `Api/Mail/src/Application/Constants/FeatureFlags.cs` — `All` et
  `ColdStartDefault`.
- `Api/Mail/src/Application/Telemetry/FeatureFlagMetrics.cs` — compteur
  `mssante_featureflag_refresh_total{status}`.

### Contenu attendu

1. **Isolation par flag.** L'échec d'évaluation d'**un** flag ne doit plus
   empêcher la publication du snapshot. Le flag fautif prend son repli déclaré
   (`FeatureFlags.ColdStartDefault`), tous les autres prennent la valeur
   réellement servie par Flagsmith. Le snapshot est publié.
2. **Un statut de rafraîchissement distinct.** Le compteur
   `mssante_featureflag_refresh_total` gagne un statut **`partial`** :
   « Flagsmith a répondu, mais des flags déclarés manquent ». Il ne doit ni
   être compté en `success` (l'exploitation doit voir l'écart) ni en `failure`
   (le service répond, et le snapshot est valide pour les autres flags —
   les confondre rend l'alerte inexploitable).
3. **Contrôle de dérive contrat / environnement.** Au **démarrage** et à
   chaque rafraîchissement partiel, journaliser **la liste nommée** des flags
   déclarés par `FeatureFlags.All` et absents de l'environnement, sous la
   politique « un log par fenêtre » déjà en place — pas un log par flag et par
   cycle. C'est le signal qui manquait le 2026-09-02.
4. **Le message de repli doit dire la vérité.** « serving last known flag
   state » ne doit être écrit que lorsqu'un état a effectivement été connu.
   Sans aucun snapshot, le log doit dire que les **replis de démarrage à
   froid** s'appliquent, et lesquels des flags concernés sont en fail-closed.
5. **Symétrie du chemin d'identité.** Le rafraîchissement par identité
   praticien (`task-274`) itère la même liste : il doit recevoir le même
   traitement, sans quoi un praticien avec des overrides retombe sur le
   snapshot d'environnement pour une raison invisible.
6. **Régression verrouillée par les tests.** Le cas « Flagsmith répond mais un
   flag déclaré est absent » doit être couvert, en vérifiant nommément que la
   valeur des flags `ai_*` **survit** à l'absence d'un flag de widget. C'est
   l'assertion qui aurait attrapé cet incident.

### Hors périmètre (explicite)

- **La création des huit flags `dashboard_widget_*` dans les environnements
  réels** est un geste d'exploitation, pas du code (le seeder
  `src/AppHost/FlagsmithSeeder.cs` ne sert que le banc, et son commentaire le
  dit). Il est mené indépendamment de cette US, et **ne la remplace pas** :
  la prochaine US qui déclarera un flag sans l'avoir créé reproduirait
  l'incident à l'identique.
- **Le rattrapage des mails passés à côté de l'étage IA** pendant la panne
  (aucun résumé, aucun embedding, aucun tag — ils le resteront après
  réactivation du flag) fait l'objet de `todo-task-290.md`.

## Definition of Done

- [ ] Build passes on api-mail (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Test : Flagsmith répond, **un** flag déclaré est absent → le snapshot est
      publié, et les flags présents portent la valeur servie par Flagsmith
- [ ] Test : ce même cas avec un flag de widget absent → `ai_pipeline` conserve
      la valeur servie par Flagsmith (**assertion nommée** — la régression de
      l'incident du 2026-09-02)
- [ ] Test : le flag absent, lui, prend bien la valeur de
      `FeatureFlags.ColdStartDefault`
- [ ] Test : `mssante_featureflag_refresh_total{status=partial}` est incrémenté
      dans ce cas, et **ni** `success` **ni** `failure`
- [ ] Test : Flagsmith injoignable → comportement de `task-199`/`task-201`
      **inchangé** (dernier état connu, puis snapshot Redis, puis repli
      déclaré) — non-régression explicite
- [ ] Test : le chemin d'identité praticien isole le flag absent de la même
      façon que le chemin d'environnement
- [ ] Test : le log de dérive nomme les flags absents, et respecte la politique
      « un log par fenêtre » (pas un log par flag ni par cycle)
- [ ] Test : sans aucun snapshot connu, le log ne prétend pas servir un
      « dernier état connu »
- [ ] Aucune donnée de santé en clair dans les logs (les logs de cette US ne
      portent que des noms de flags — à vérifier, y compris sur le chemin
      d'identité où l'identifiant est l'adresse MSSanté du praticien)
- [ ] `GET /api/v1/FeatureFlag` a au moins 1 test d'intégration couvrant le cas
      partiel (rule 1b)

## Manual Test Plan

- **Lancer le backend** : `cd Api/Mail && dotnet run --project src/AppHost`
  (le profil AppHost démarre Flagsmith et le seed via `FlagsmithSeeder`).
- **Reproduire l'incident** : dans l'UI Flagsmith (`http://localhost:8000`,
  projet `HealthPlatform.Mss`, environnement `Development`), **archiver ou
  supprimer** le flag `dashboard_widget_mail_counters` — un seul suffit. Poser
  `ai_pipeline` à **`true`** dans la même UI, pour que le contrôle soit
  discriminant.
- **Écran / URL à ouvrir** : `GET http://localhost:<port>/api/v1/FeatureFlag`
  (l'état complet des flags tel que l'API le voit).
- **Ce que l'humain doit voir** :
  - `ai_pipeline` ressort **`true`** (avant correctif : `false`) ;
  - `dashboard_widget_mail_counters` ressort à son repli déclaré (`true`) ;
  - dans les logs, **une** ligne nommant le flag absent, et **aucune**
    mention de « serving last known flag state » ;
  - le compteur `mssante_featureflag_refresh_total{status=partial}` avance sur
    l'endpoint de métriques Prometheus.
- **Vérifier la conséquence métier** — le seul contrôle qui prouve la valeur
  pour le praticien : ouvrir un mail clinique porteur d'un document, puis
  `GET /api/v1/mail/folders/INBOX/emails/summary/{uid}` → **200 avec un
  résumé**, alors qu'avant correctif la même requête répondait 404 « AI summary
  is not available ».
- **Remettre le flag** dans l'UI Flagsmith et vérifier le retour au nominal :
  le log `[FeatureFlag] Flagsmith refresh recovered … flag state is live again`
  doit apparaître.
- **Données de test** : aucune donnée de santé réelle. Les mails du banc
  (`loadtest-skill`) sont synthétiques.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors exigence DSR directe — mécanique interne de
  robustesse ; elle **protège** en revanche des fonctionnalités du couloir
  (résumé et indexation des documents cliniques reçus par MSSanté)
- **Exigences DSR honorées** : non applicable — aucune exigence DSR ne porte
  sur le pilotage interne des feature flags
- **INS** : non applicable — aucun identifiant patient n'est manipulé ; le
  service n'échange que des noms de flags booléens
- **Authentification PS** : inchangée — PSC / e-CPS, niveau eIDAS substantiel,
  déjà en place sur les endpoints concernés (`PscIdentity__Enforce: true` en
  Staging). Cette US ne touche pas la chaîne d'authentification
- **Habilitations** : inchangées — le chemin d'identité de `task-274` utilise
  l'adresse MSSanté du praticien comme identifiant Flagsmith, sans contrôle
  d'habilitation supplémentaire
- **Interop CI-SIS** : non applicable — aucun échange métier. Effet **indirect**
  à noter : l'étage IA éteint prive d'indexation les documents CDA reçus, dont
  le traitement lui-même (via `interop-cda` + Schematron) reste inchangé
- **Tracé PGSSI-S** : évènements à journaliser — (a) rafraîchissement partiel
  avec la liste nommée des flags absents, (b) application des replis de
  démarrage à froid, (c) retour au nominal. Ce sont des évènements
  d'**exploitation**, sans donnée de santé : conservation alignée sur la
  politique de logs technique de la plateforme, et non sur la durée de 6 ans
  des traces d'accès au dossier
- **Consentement patient** : non applicable — aucun traitement de donnée
  patient n'est créé ni modifié
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — Staging et Production de la plateforme. Sans
  objet pour cette US, qui n'ajoute aucun stockage de DSCP
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau, aucune donnée
  personnelle supplémentaire collectée. À noter tout de même : l'identifiant
  Flagsmith du chemin d'identité **est** une donnée personnelle du praticien
  (adresse MSSanté nominative) ; le DOD exige qu'elle ne fuite pas dans les
  logs de dérive
