# todo-task-315.md — Une indisponibilité de la messagerie cesse d'être silencieuse : l'analyse rend un résultat, les sessions se rétablissent, et le médecin est prévenu

**Repos**: api-mail, client-blazor, client-angular, client-mobile
**Dependencies**: — (aucune ; n'entre en conflit avec aucune US en vol)
**Epic**: E015
**Priorité**: **1** — **perte de donnée médicale silencieuse**, du même ordre que
`task-196` et `task-290`. Pendant 80 minutes, l'application a répondu « ✅ analysé »
à chaque demande **sans écrire un seul document dans un dossier patient**, et rien —
ni log d'erreur, ni métrique, ni sonde de santé, ni message à l'écran — ne l'a signalé.

> **Origine** : campagne de charge du 2026-09-16/17, palier 1000 (passe d'hydratation).
> Rapport : `Docs/audits/api-mail-loadtest-journey-500-audit-basecommune-20260917.md`.
> Cause **mesurée**, puis **lue dans le code**, puis **suivie jusque dans les trois
> fronts**.

## Objective

Qu'une indisponibilité du serveur de messagerie **se voie** — jusqu'à l'écran du
médecin — et que l'application **s'en remette d'elle-même** au lieu de rester bloquée
jusqu'au prochain redémarrage.

Le médecin doit pouvoir répondre à une question simple qu'il ne peut pas poser
aujourd'hui : *« mes documents ne se rattachent pas — est-ce qu'il n'y en a pas, ou est-ce
que quelque chose est cassé ? »*

### Pourquoi les quatre repos dans une seule US — règle 11

La version backend-seule de cette US a été écrite puis **abandonnée** : vérification faite
dans les trois fronts, **aucun** ne sait quoi faire d'un `503` sur ce chemin. Un backend
qui rend une erreur correcte que personne n'affiche est de la plomberie, pas de la valeur
pour le médecin — et en Angular ce serait même un **recul**, l'observable échouant sans
handler d'erreur là où il n'y avait qu'une absence silencieuse.

| Front | Appel | Traitement actuel de l'erreur |
|---|---|---|
| `client-angular` | `enrich/sync` à l'ouverture d'un dossier (`mail-list.component.ts:222`) | `.subscribe(() => {…})` — **aucun handler d'erreur** |
| `client-blazor` | `enrich/async` **et** `enrich/sync` (`MailService.cs:40-66`) | `catch (Exception ex) { logger.LogError(…); }` — **erreur avalée** |
| `client-mobile` | `enrich/sync` (`mss-api.service.ts:294`) | même forme qu'Angular |

Et `canAccessImap`, que cette US rend enfin sincère, n'est aujourd'hui **déclaré que dans
un type** (`sync.model.ts:31`) et **consommé nulle part**.

## Ce qui a été mesuré — tir `journey-1000-hydratation-20260916`, 3 h 30 à 1000 médecins

| Grandeur | t+120 min | t+130 min | t+210 min (fin) |
|---|---|---|---|
| Messages analysés (`mssante_enrichment_message_duration_seconds_count`, brut) | 71 205 | **72 101** | **72 101** |
| Requêtes HTTP servies (cumul) | 676 982 | 769 094 | **1 721 672** |
| Sessions IMAP **actives** (`mssante_imap_sessions_active`) | 2 224 | 1 511 | 2 177 |
| Sessions IMAP **connectées** (`mssante_imap_sessions_connected`) | 2 224 | **0** | **0** |
| Réplicas exportant leurs métriques | 5 | 5 | 5 |

**Le compteur d'analyse est gelé pendant 80 minutes** alors que l'application sert
**950 000 requêtes de plus** et que les cinq réplicas publient toujours : ni trou
d'instrumentation, ni machine saturée, ni décroissance progressive. Un arrêt net, à la
minute où **toutes** les sessions IMAP passent de connectées à zéro.

Sur la même période, `enrich/sync` **continue d'être appelé au même rythme** (≈ 4 250
requêtes par tranche de 20 min) et répond **`HTTP 200`, zéro erreur**, en **2 à
3 secondes** — donc pas le court-circuit « déjà analysé », qui répond en ~25 ms. Contrôle
nominatif dans Seq : `loadtest-815` appelle à t+170 min, reçoit `200` en 2 334 ms, et
**termine le tir avec `MailContents = 0`**. En base : hydratation pleine jusqu'à l'index
~640, dégradée jusqu'à ~700, **nulle au-delà** — 72 101 ÷ 98 ≈ **736 médecins**, exactement
le front observé.

**Conséquence de terrain** : 264 médecins sur 1000 n'ont reçu aucun document, et la
plateforme a rapporté un succès pour chacun d'eux.

## La cause, dans le code

`MailController.EnrichEmailsSyncAsync` (`src/Api/Controllers/V1/MailController.cs:483`) :

```csharp
await serviceImplementation.EnrichEmailsAsync(decodedFolderName, uids, cancellationToken);
logger.LogInformation("✅ Enriched {Count} UIDs", uids.Count);
return Ok();
```

`ImapService.EnrichEmailsAsync` (`src/Application/Services/Implementation/ImapService.cs:1341`) :

```csharp
foreach (var chunkUids in ChunkForEnrichment(pendingUids, EnrichFetchChunkSize))
{
    var chunkFetch = await FetchEnrichmentChunkAsync(folder, chunkUids, cancellationToken);
    fetched.AddRange(chunkFetch.Fetched);
    if (chunkFetch.FolderUnavailable)
    {
        break;            // abandon du RESTE du lot
    }
}

if (fetched.Count == 0)
{
    return;               // sortie SILENCIEUSE : ni exception, ni log, ni compteur
}
```

Quatre défauts empilés :

1. **`EnrichEmailsAsync` rend `Task`.** Le contrôleur ne peut pas savoir combien de
   messages ont été analysés ; il journalise `uids.Count`, le nombre **demandé**. Les
   trois interfaces (`IImapService`, `IImapEmailFetchService`, `IBackgroundImapService`)
   portent la même signature muette.
2. **`FolderUnavailable` est une information que le code possède et jette.**
   `SingleMailFetch` et `EnrichmentChunkFetch` la transportent jusqu'à la boucle, qui s'en
   sert pour sortir — puis la perd.
3. **Le chemin asynchrone ment aussi, et personne ne peut le rattraper.**
   `EnrichEmailsBackgroundAsync` (`MailController.cs:431`) empile dans
   `IBackgroundTaskQueue` et journalise, **inconditionnellement** :
   `[Enrich] ✅ Completed {Count} UIDs (async)` — avec le nombre demandé. Le `202 Accepted`
   est déjà parti : **il n'y a plus d'appelant à qui rendre une erreur**. C'est le chemin
   que `client-blazor` utilise par défaut.
4. **La sonde de santé ne consulte pas les connexions.**
   `ConnectionModeService.CanAccessImap => IsOnlineMode` : un drapeau de mode, pas un état.
   Pendant toute la panne, `GET /api/v1/connection/status` a répondu
   `{"mode":"online","canAccessImap":true}`.

> ⚠️ **Le chemin `enrich/sync` n'est PAS une file.** `enrich/async` en est une
> (`IBackgroundTaskQueue`), `enrich/sync` est purement synchrone. Mettre `sync` en file
> **sans** les correctifs ci-dessous reproduirait la panne avec une indirection de plus.
> La reprise par travailleur de plateforme est un chantier **ultérieur** (les UID non
> traités restent déjà `pending` — cf. `ImapService.cs:1398`).

## Portée

### 1. Backend — l'analyse rend un résultat, et l'échec devient une erreur typée

`EnrichEmailsAsync` rend un résultat à quatre comptes : **demandés**, **déjà analysés**
(court-circuit), **analysés**, **non joignables**. Les trois interfaces sont alignées.

**Chemin synchrone** (`enrich/sync`) :
- au moins un message analysé, ou tous déjà analysés ⇒ **`200`**, comptes réels dans le
  corps **et** dans le log (`✅ Enriched {Analysed}/{Requested}`) ;
- **aucun message analysé alors qu'il en restait, parce que la messagerie n'est pas
  joignable** ⇒ **`503`** via `UnavailableException`, donc `ProblemDetails` RFC 7807 produit
  par le `GlobalExceptionHandler` — **règle 12, non négociable**. Aucun `try/catch` ad hoc,
  aucun `StatusCode(503, "...")`.

**Chemin asynchrone** (`enrich/async`) : le `202` reste (c'est le contrat), mais la tâche
de fond **journalise le compte réel**, **incrémente un compteur d'échec**, et **remet en
file le reliquat non joignable** avec un retard borné et un nombre d'essais plafonné —
jamais une boucle de reprise infinie.

Le `detail` exposé au client nomme l'indisponibilité, **jamais** le serveur IMAP, son hôte,
le dossier, un UID ni un fragment de message.

### 2. Backend — une session dont la connexion est perdue se rétablit ou disparaît

2 200 sessions sont restées **actives sans être connectées pendant 80 minutes**, jamais
reconnectées, jamais évincées. Après cette US :

- une session dont le lien IMAP est tombé est **reconnectée au prochain usage**, ou
  **évincée du pool** si la reconnexion échoue — jamais conservée inutilisable ;
- reconnexions et évictions sont **journalisées** et **comptées** ;
- le rétablissement ne dépend d'**aucun** redémarrage de réplica.

### 3. Backend — la santé reflète les connexions réelles

`CanAccessImap` cesse d'être un alias d'`IsOnlineMode` : `GET /api/v1/connection/status`
rend `canAccessImap: false` quand le compte de sessions **connectées** est nul alors que des
sessions **actives** existent — exactement la signature mesurée.

### 4. Fronts — le médecin est prévenu, et il sait que ce n'est pas perdu

Les trois fronts traitent le `503` sur le chemin d'analyse et affichent un message dont le
sens est : **« La messagerie est momentanément indisponible. Les documents seront rattachés
dès son rétablissement. »** Deux qualités non négociables : il dit que **ce n'est pas une
absence de documents**, et il dit que **rien n'est perdu**.

- **`client-blazor`** — `MailService.EnrichEmailsAsync` / `EnrichEmailsSyncAsync` cessent
  d'avaler l'exception : `IErrorNotificationService.NotifyConnectionError()` (le mécanisme
  existe déjà) sur `503`, journalisation conservée pour le reste.
- **`client-angular`** — `enrichEmails` (`mail-list.component.ts:220`) gagne un handler
  d'erreur, lit le `ProblemDetails` (`core/models/problem-details.model.ts` existe déjà) et
  suit le motif `catchError` / `toError<T>` déjà employé par `mailbox-accounts.service.ts`.
  La liste reste affichée — **on ne vide pas l'écran du médecin sur une panne d'analyse**.
- **`client-mobile`** — `ActionFeedbackService` (`ToastController`) porte le message.

Le message est **non bloquant** (pas de modale), **non répété en rafale** (une occurrence
par épisode d'indisponibilité, pas une par lot), et **disparaît au rétablissement**.

## Definition of Done

**Backend — `api-mail`**

- [ ] Build passe (0 erreur) ; tests passent (0 échec)
- [ ] `EnrichEmailsAsync` rend un résultat à quatre comptes ; `IImapService`,
      `IImapEmailFetchService`, `IBackgroundImapService` alignées
- [ ] **Test unitaire — LE CAS DU 2026-09-16** : `FolderUnavailable` au premier sous-lot,
      aucun message lu, des UID restant à traiter ⇒ `UnavailableException`.
      **Ce test doit échouer sur le code actuel**
- [ ] Test unitaire : lot entièrement déjà analysé ⇒ `200`, `Analysed=0`,
      `AlreadyAnalysed=N`, **aucune** exception — le court-circuit n'est pas une panne
- [ ] Test unitaire : indisponibilité au 3ᵉ sous-lot ⇒ `200`, le travail déjà payé est
      persisté, les UID non traités restent `pending`
- [ ] Test d'intégration : `enrich/sync` messagerie injoignable ⇒ **`503`** en
      `application/problem+json` conforme RFC 7807, produit par le `GlobalExceptionHandler`
- [ ] **Test de non-fuite (bloquant)** : le `detail` ne contient ni hôte IMAP, ni nom de
      dossier, ni UID, ni INS/NIR, ni fragment de contenu MSSanté/CDA
- [ ] Test : `enrich/async` journalise le compte **analysé**, incrémente le compteur
      d'échec, et **remet en file** le reliquat non joignable — essais plafonnés, retard
      borné, aucune boucle infinie
- [ ] Le log de succès porte le nombre **analysé** sur les deux chemins ; un test le
      vérifie sur un lot partiellement traité
- [ ] Test unitaire : session au lien tombé ⇒ **reconnectée** au prochain usage ; si la
      reconnexion échoue ⇒ **évincée** du pool
- [ ] Test unitaire : aucune session ne reste `active` et non `connected` au-delà d'un
      usage — inversion exacte du défaut mesuré
- [ ] Compteurs exposés **et exportés** (`AddMeter` vérifié — cf. F-297-M) : reconnexions
      tentées / échouées, sessions évincées, messages non joignables, reprises en file
- [x] ~~Test unitaire : `CanAccessImap` rend `false` quand…~~ — **RETIRÉ le 2026-09-17**, infirmé par le tir de vérification (voir « Le point 3 retiré »)
- [x] ~~Test d'intégration : `connection/status` reflète l'état des connexions~~ — **RETIRÉ le 2026-09-17**, même raison
- [ ] Aucune donnée de santé en clair dans les logs ajoutés
- [ ] Évènements PGSSI-S journalisés : indisponibilité constatée, reconnexion, éviction

**Fronts — `client-blazor`, `client-angular`, `client-mobile`**

- [ ] Les trois fronts **ne produisent plus d'erreur non gérée** sur `503` du chemin
      d'analyse (test de composant par front)
- [ ] Les trois affichent le message d'indisponibilité, **non bloquant**, **une seule fois
      par épisode** (test : trois `503` consécutifs ⇒ une seule notification)
- [ ] La liste des messages **reste affichée** — aucun écran vidé sur panne d'analyse
- [ ] Aucune chaîne en dur dans l'UI : le message passe par le mécanisme de traduction du
      module
- [ ] `data-testid` sur l'élément d'alerte (Angular, mobile)
- [ ] Blazor : `EnrichEmailsAsync` / `EnrichEmailsSyncAsync` n'avalent plus l'exception ;
      `NotifyConnectionError()` sur `503`
- [ ] Angular : `enrichEmails` lit le `ProblemDetails` et suit le motif `catchError` /
      `toError<T>` existant
- [ ] Mobile : message porté par `ActionFeedbackService`
- [ ] Builds et tests verts sur les trois fronts

## Manual Test Plan

**Lancer le banc** (profil loadtest, serveurs mail locaux — cluster inutile) :

```bash
cd Api/Mail
taskkill /F /IM dcp.exe /T 2>/dev/null
rm -rf ~/.dcp/state.elevated ~/.dcp/mruPorts.elevated.list
dotnet run --project src/AppHost --launch-profile https-load-test
dotnet run --project tests/mss.mail.loadtest.seed -- --users 3 --messages 20 \
  --api http://127.0.0.1:5052 \
  --registry "Host=127.0.0.1;Port=5432;Username=postgres;Password=postgres;Database=mss_registry_loadtest"
```

⚠️ Le registre de banc doit être une **base dédiée** : le seed refuse d'écrire dans un
registre portant un compte hors banc (constaté le 2026-09-16 sur `mss_registry`).

**Étape 1 — nominal (API).**

```bash
curl -i -X POST "http://127.0.0.1:5052/api/v1/mail/folders/INBOX/emails/enrich/sync" \
  -H "Content-Type: application/json" -H "X-Test-Bypass: loadtest-local-only" \
  -H "Client-Email: loadtest-1@loadtest.local" \
  -H "Client-Psc-Sub: 00000000-0000-4000-8000-000000000001" \
  -H "Client-Rpps: 90000000001" -H "Client-Session-Id: sess-1" -H "X-PSC-Token: loadtest" \
  -d '[1,2,3,4,5]'
```

**Attendu** : `200`, corps indiquant **5 analysés**, log `✅ Enriched 5/5`.

**Étape 2 — rejouer le même lot.** **Attendu** : `200`, **0 analysé, 5 déjà analysés**,
aucune erreur.

**Étape 3 — LE CAS DU DÉFAUT (API).** Couper le serveur IMAP :

```bash
docker stop $(docker ps --filter name=loadtest-dovecot --format '{{.Names}}')
```

Rejouer l'étape 1 sur les UID **6 à 10** (jamais analysés). **Attendu** : **`503`**,
`application/problem+json`, corps RFC 7807 annonçant l'indisponibilité ; **aucune** mention
d'hôte, dossier, UID ou contenu ; **aucun** `✅ Enriched` dans les logs.
*Avant cette US : `200` et `✅ Enriched 5 UIDs`.*

**Étape 4 — la santé le dit.**

```bash
curl -s "http://127.0.0.1:5052/api/v1/connection/status" -H "X-Test-Bypass: loadtest-local-only" \
  -H "Client-Email: loadtest-1@loadtest.local" \
  -H "Client-Psc-Sub: 00000000-0000-4000-8000-000000000001" \
  -H "Client-Rpps: 90000000001" -H "X-PSC-Token: loadtest"
```

**Attendu** : `canAccessImap: false`. *Avant : `true`, en pleine panne.*

**Étape 5 — LE MÉDECIN, sur les trois fronts.** Dovecot **toujours arrêté**, ouvrir la
messagerie et sélectionner un dossier contenant des messages non analysés, successivement
sur `client-blazor`, `client-angular` et `client-mobile`.

**Attendu, identique partout** :
- un message non bloquant du type **« La messagerie est momentanément indisponible. Les
  documents seront rattachés dès son rétablissement. »** ;
- **la liste des messages reste affichée** ;
- rafraîchir trois fois ⇒ **une seule** notification, pas trois ;
- console navigateur : **aucune erreur non gérée**.

*Avant cette US : rien à l'écran, et en Angular une erreur non gérée en console.*

**Étape 6 — le rétablissement, sans redémarrage.**

```bash
docker start $(docker ps -a --filter name=loadtest-dovecot --format '{{.Names}}')
```

Attendre que le conteneur soit prêt, puis **rejouer l'étape 3 telle quelle**, **sans
redémarrer l'AppHost ni aucun réplica**. Puis rafraîchir le dossier sur un front.

**Attendu** : `200`, **5 analysés** ; la notification disparaît ; les documents médicaux
apparaissent. *Avant : l'analyse restait à zéro indéfiniment — 80 minutes mesurées au banc,
sans reprise.*

**Étape 7 — la preuve en base.**

```bash
docker exec postgres-pgvector psql -U postgres \
  -d $(docker exec postgres-pgvector psql -U postgres -tAc \
       "select datname from pg_database where datname like 'u\_90000000001\_%' limit 1" | tr -d ' ') \
  -tAc 'select count(*) from "MailContents"'
```

**Attendu** : 10 (les 5 de l'étape 1 + les 5 de l'étape 6). **C'est ce contrôle qui
tranche** : au banc, l'API annonçait des succès pendant que ce compte restait à 0.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors vague — correctif de robustesse sur une fonction existante,
  n'introduit aucune exigence DSR nouvelle
- **Exigences DSR honorées** : aucune nouvelle. La US **protège** l'alimentation du dossier
  patient par documents CDA reçus en MSSanté, déjà couverte par l'existant
- **INS** : non applicable — la US ne touche ni au calcul, ni au statut, ni au rapprochement
  de l'INS. Elle garantit que les documents qui **portent** une INS arrivent effectivement
  jusqu'au rapprochement, au lieu d'être perdus en silence
- **Authentification PS** : inchangée — PSC / e-CPS, niveau eIDAS substantiel
- **Habilitations** : inchangées — RPPS porté par le contexte utilisateur existant
- **Interop CI-SIS** : CDA r2 — **format inchangé**. La US porte sur la fiabilité de
  l'acheminement vers l'analyse, pas sur le contenu ni sur le parsing
- **Tracé PGSSI-S** : trois évènements ajoutés — *indisponibilité constatée lors d'une
  analyse*, *reconnexion de session*, *éviction de session*. Conservation alignée sur les
  traces techniques existantes (365 jours, `AuditRetentionPolicy`). Aucun ne porte de
  donnée de santé
- **Consentement patient** : non applicable — aucun partage, aucune publication DMP /
  Mon Espace Santé introduits
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — le chemin manipule des DSCP (corps MSSanté, documents CDA).
  Aucune donnée nouvelle créée, stockée ni transmise
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau. La US **réduit** un risque
  d'intégrité : des documents médicaux qui n'entraient jamais dans le dossier sans que
  personne en soit informé

## Ce que cette US ne fait pas

- **Elle ne met pas `enrich/sync` en file.** Le chemin reste synchrone ; seul `enrich/async`
  gagne une reprise bornée. La reprise généralisée par travailleur de plateforme est un
  chantier distinct, à instruire **après** celui-ci.
- **Elle ne cherche pas pourquoi les sessions se sont déconnectées** le 2026-09-16.
  L'hypothèse — redémarrage du pod Dovecot/Toxiproxy du cluster — n'est pas vérifiable
  depuis ce poste (`kubectl` refusé), et **n'a pas besoin de l'être** : quelle que soit la
  cause, l'application doit la voir et s'en remettre.
- **Elle ne corrige pas la chauffe du banc** (`journey_warmup_completed` valait 1,0 alors
  que 264 médecins n'avaient rien reçu). Finding de harnais séparé : la chauffe doit se
  vérifier en base, pas au code HTTP.

## Branches

- `api-mail` (pushed) : `feat/task-315-messagerie-indisponible-visible` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-315-messagerie-indisponible-visible
- `client-blazor` (pushed) : `feat/task-315-messagerie-indisponible-visible` — https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-315-messagerie-indisponible-visible
- `client-mobile` (pushed) : `feat/task-315-messagerie-indisponible-visible` — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-315-messagerie-indisponible-visible
- `client-angular` (code-only) : la forge écrit sur la branche actuellement checked out dans `Client/Angular/` — instantané au `/start` : **`feature/nova-rewriting-mss`**. L'humain garde branche, commit, push et PR TFS.

> Pré-vol : `api-mail`, `client-blazor`, `client-mobile`, `dtos-mss`, `sdk`, `interop-cda` tous sur `develop`. `host` écarté (pas de `.git` — cf. l'avertissement du CLAUDE.md). `dtos-mss` **non auto-inclus** (branche paresseuse depuis le 2026-09-16) : aucun contrat n'est attendu dans cette US.
>
> Le banc de charge a été rendu au `/start` pour libérer les binaires d'`api-mail`. **Les 1000 bases hydratées sont intactes** (aucun `reset-state.sh` joué) — la campagne suivante n'aura pas à repayer les 3 h 30 d'hydratation.

## Timings

*(généré par `tools/timing/report.sh --task task-315 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 1 min 52 s | — | — | — | — |
| /develop | ok | 31 min 49 s | 1 (26 s) | 7 (5 min 40 s) | — | api-mail 0B/3T, client-blazor 0B/1T, client-mobile 0B/2T, client-angular 1B/1T |
| /sonar | ok | 7 min 38 s | — | — | 1 (4 min 40 s) | — |
| /lint-angular | ok | 3 min 11 s | 1 (21 s) | 1 (13 s) | — | 1 itération(s), client-angular 1B/1T |
| /lint-mobile | ok | 25 s | — | — | — | — |
| /verify-visual | skipped | 18 s | — | — | — | Tools/visual-verify absent du workspace ; aucun Stitch design log |
| /review | ok | 5 min 22 s | 3 (19 s) | 4 (2 min 05 s) | — | api-mail 1B/1T, client-blazor 1B/1T, client-mobile 1B/1T, client-angular 0B/1T |
| /tech-writer | ok | 3 min 21 s | — | — | — | — |
| **Total cycle** | | **53 min 58 s** | **5 (1 min 08 s)** | **12 (7 min 59 s)** | **1 (4 min 40 s)** | |

Autres commandes mesurées : lint ×2 (28 s)

## Develop log

### Backend — `api-mail` (poussé, `3380a681` + `simplify pass`)

- `EnrichmentOutcome` (demandés / déjà analysés / analysés / injoignables) ; les
  trois interfaces alignées.
- `enrich/sync` → **503** `UnavailableException` quand rien n'a pu être lu alors
  qu'il restait à faire. Symétrique du 503 que **task-293** avait déjà posé, dans
  cette même méthode, pour les échecs d'extraction — avec ce commentaire :
  « le 200 qui a masqué l'incident du 2026-09-08 ». Le précédent existait, il ne
  couvrait simplement pas la connexion perdue.
- `enrich/async` → compte réel dans le log, `mssante_enrichment_unreachable_messages_total`,
  et remise en file du reliquat (3 essais, retard croissant, lot complet rejoué —
  idempotent puisque les déjà-analysés court-circuitent).
- Balayage de sessions : éviction de celles dont la voie IMAP est ouverte et le
  lien tombé.
- `CanAccessImap` cesse d'être un alias d'`IsOnlineMode`.

> ⚠️ **Correction de conception en cours d'implémentation.** La première version
> de la sonde testait `ActiveSessionCount > 0 && ConnectedSessionCount == 0` —
> et aurait déclaré la messagerie morte **au démarrage**, une session qui n'a pas
> encore ouvert de voie IMAP étant légitimement active et non connectée. C'est le
> test d'invariant du balayage qui l'a révélé, **en contredisant son voisin**.
> D'où `DisconnectedSessionCount`, qui ne compte que les liens réellement tombés.

**Vérification du DOD « ce test doit échouer sur le code d'origine »** : garde
retirée temporairement, `EnrichEmailsSync_NothingReadWhileWorkRemained` échoue sur
`Assert.Throws() Failure: No exception was thrown` — le 200 du 16/09. Garde
restaurée, test vert.

**Tests** : 183 domaine + 492 infra + 2 488 application + 837 API + 507 intégration,
**0 échec**.

### `client-blazor` (poussé, `a7db495`)

`PostAndGetStatusAsync` (le booléen d'`IsSuccessStatusCode` rendait un 503
indistinguable d'un 500), `NotifyMailServerUnavailable`, et
`OutageNotificationGate` — la règle « une fois par épisode » isolée en unité
**pure**, parce que `HttpRequestService` est une classe concrète à méthodes non
virtuelles, donc non mockable. **260 tests verts.**

### `client-mobile` (poussé, `27a3b8d`)

`MailOutageNotifierService` + branchement des deux appels d'analyse, qui étaient
`subscribe({ error: () => undefined })`. **861 tests verts.**

### `client-angular` (code-only — aucune opération git)

Signal `mailServerUnavailable` dans `MailStateService`, handler d'erreur sur
`enrichEmails`, bandeau non bloquant `data-testid="mail-server-unavailable"`.
**380 tests verts, build `nx build mss` vert.** Les fichiers restent **modifiés
non commités**, mêlés au travail en cours de l'humain sur
`feature/nova-rewriting-mss`.

> ⚠️ **Divergence assumée sur un item du DOD.** « Aucune chaîne en dur dans l'UI :
> le message passe par le mécanisme de traduction du module » est **sans objet
> pour `client-angular`** : le module MSS n'a pas d'i18n, et c'est une convention
> **documentée** — `mail-undo-toast.component.ts` et `mailbox-quota-widget.component.ts`
> portent tous deux « does not use ngx-translate — French labels are hardcoded ».
> Introduire un mécanisme de traduction pour un seul bandeau sortirait du périmètre
> et diviserait la convention du module. Le libellé suit donc ses voisins.

## Sonar log

Analyse du 2026-09-17 07h38 UTC sur `feat/task-315-messagerie-indisponible-visible`
(projet `healthplatform-api-mail`, build Release + 5 suites avec couverture
OpenCover).

| KPI | Baseline (16/09) | Final (17/09) | Cible | Verdict |
|---|---|---|---|---|
| `bugs` | 0 | **0** | 0 | ✅ |
| `vulnerabilities` | 0 | **0** | 0 | ✅ |
| `new_bugs` | 0 | **0** | 0 | ✅ |
| `new_vulnerabilities` | 0 | **0** | 0 | ✅ |
| `sqale_rating` | A | **A** | A | ✅ |
| `reliability_rating` | A | **A** | — | ✅ |
| `security_rating` | A | **A** | — | ✅ |
| `coverage` | 87,8 % | **87,8 %** | 95 % | ❌ dette héritée |
| `new_coverage` | 85,9 % | **85,9 %** | 95 % | ❌ dette héritée |
| `code_smells` | 228 | **228** | — | inchangé |
| `new_code_smells` | 35 | **35** | — | inchangé |
| **Quality Gate** | — | **ERROR** | OK | ❌ — voir ci-dessous |

**Aucune itération de nettoyage n'a été nécessaire : task-315 n'introduit
aucune issue Sonar.** Vérifié fichier par fichier plutôt que déduit du total :

| Fichier touché | Issues ouvertes |
|---|---|
| `EnrichmentOutcome.cs` | 0 |
| `MailController.cs` | 0 |
| `ConnectionModeService.cs` | 0 |
| `MailClientSessionManager.cs` | 0 |
| `MailProcessingMetrics.cs` | 0 |
| `ImapService.cs` | 1 — `S3604` **ligne 83**, préexistante (le diff porte sur 1341-1490) |
| `BackgroundImapService.cs` | 1 — `S107` **ligne 60**, préexistante (le diff porte sur 180-290) |

**Couverture du code neuf de la task** : `EnrichmentOutcome.cs` **100 %**
(6 lignes à couvrir, 0 non couverte), `ConnectionModeService.cs` **100 %**
(10 / 0). Les 85,9 % de `new_coverage` du projet sont de la dette antérieure,
portée par `ImapService.cs` (81,4 %, 307 lignes non couvertes sur 1 714) et
`MailController.cs` (94,4 %).

**Quality Gate ERROR — une seule condition, et elle n'est pas de cette task** :
`new_security_hotspots_reviewed` à 0 % pour un seuil de 100 %. L'unique hotspot
concerné est `TenantRegistryMigrator.cs:106` (log-injection), issu du chantier
registre (task-299/300). `agents/sonar-targets.yml` pose que **les hotspots sont
revus manuellement par un humain** et ne sont pas une cible `/sonar` : il est
signalé ici pour arbitrage, pas corrigé d'office.

Les 5 suites restent vertes sous configuration Release : 183 / 2 488 / 492 / 837 / 507.

## Lint log — `client-angular`

Mode A (chaîné), scope `tag:scope:mss` (projets `mss` + `mss-lib`), base
`origin/next`.

| | Erreurs | Warnings |
|---|---|---|
| Baseline | **28** | 41 |
| Final | **0** | 41 |

**Une seule itération, et un seul fichier concerné — le mien.** Les 28 erreurs
étaient toutes `prettier/prettier` « Insert tab » sur
`mail-list.component.ts`, lignes 243-270 : en imbriquant le corps du `subscribe`
dans `next: () => {`, je n'avais ré-indenté que les trois premières lignes.

> ⚠️ **L'auto-fixer a été lancé sur ce seul fichier**, et non sur le scope MSS
> entier comme le ferait le playbook. Raison : l'humain a **11 fichiers modifiés
> non commités** dans `Client/Angular/` (travail en cours sur
> `feature/nova-rewriting-mss`), et un `--fix` large les aurait réécrits au
> passage. Le résultat est le même — 0 erreur sur le scope — sans toucher à ce
> qui ne m'appartient pas.

Les **41 warnings restants sont préexistants** et hors périmètre : `max-lines`
(fichiers > 500 lignes), `jsdoc/require-example`, `complexity` sur
`classifyDocument`. Best-effort : acceptés, non bloquants.

Re-validation après auto-fix : **380 tests verts** (46 fichiers), `nx build mss`
vert.

**Aucune opération git sur `client-angular`** — mode code-only. Les fichiers de
task-315 restent modifiés non commités, mêlés au travail en cours de l'humain,
qui garde branche, commit, push TFS et ouverture de PR.

### Conventions apprises

Aucune entrée ajoutée à `conventions/angular.md` : les 28 erreurs ont été
corrigées par **l'auto-fixer**, et le protocole ne comptabilise que les règles
corrigées **manuellement** (les fixes de l'auto-fixer sont gratuits).

## Lint mobile log

Mode A (chaîné), branche `feat/task-315-messagerie-indisponible-visible`.

`npm run lint` → **`All files pass linting.`**

| | Erreurs | Warnings |
|---|---|---|
| Baseline | **0** | **0** |
| Final | **0** | **0** |

**Aucune itération, aucun fix, donc aucun commit** — l'automation git de cette
étape n'avait rien à pousser. Le code mobile de task-315 (`MailOutageNotifierService`,
son spec, et les deux points de branchement) passe le lint du premier coup.

Rien à ajouter à `conventions/angular.md` : aucune règle n'a été corrigée, ni
manuellement ni par l'auto-fixer.

## Visual verify log

**Étape sautée — outillage absent.** `Tools/visual-verify/` n'existe pas dans le
workspace (ni `capture.mjs`, ni `screens.json`, ni `frame.mjs`). Skip
best-effort conformément au playbook, la chaîne continue. Même constat qu'au
cycle de task-304.

La task n'a par ailleurs **aucun `## Stitch design log`** : elle ne crée aucun
écran. Le changement mobile est un service (`MailOutageNotifierService`), son
spec, et deux points de branchement.

> ⚠️ **Ce que ce skip laisse non vérifié, et il ne faut pas le taire.** J'ai
> modifié `inbox.page.ts` — une **page**. Un écran blanc ou un crash de
> navigation est exactement le défaut que les tests unitaires ne voient pas, et
> c'est la seule sévérité **bloquante** de cette étape. Les 861 tests et le
> `npm run build` sont verts, mais aucun des deux ne prouve que l'inbox
> s'affiche.
>
> À couvrir au test manuel : l'**étape 5** du Manual Test Plan ouvre justement
> la messagerie sur les trois fronts, Dovecot arrêté, et exige que « la liste
> des messages reste affichée ». C'est elle qui portera cette vérification au
> HAG.


## Tests d'intégration — ajoutés après coup (2026-09-17)

> ⚠️ **Manquement de la forge.** Les deux items de DOD exigeant un test
> d'intégration (lignes 196 et 213) **n'ont pas été livrés** au cycle initial, et
> `/review` a pourtant rapporté « DOD : tous les items vérifiés ». Le contrôle
> item par item n'a pas été fait ; il a été **déduit** du vert de la suite. La
> règle 1b du CLAUDE.md était également en défaut (un test d'intégration par
> endpoint). Corrigé sur signalement humain, commit `68ad7e9c`, poussé sur la
> PR #243 déjà ouverte.

`tests/mss.mail.integration.tests/Api/MailServerUnavailableEndpointIntegrationTests.cs`
— **6 tests** montés sur `TestServer` avec le pipeline d'erreurs **de
production** (`AddMssProblemDetails()` + `AddExceptionHandler<GlobalExceptionHandler>()`
+ `UseExceptionHandler()`).

**Ce que les tests unitaires ne prouvaient pas.** `MailControllerTests` vérifie
que le contrôleur **lève** une `UnavailableException` ; il n'établit pas qu'elle
devienne un **503 `application/problem+json`**. Cela dépend de trois pièces de
câblage qu'aucun test unitaire ne traverse — et c'est précisément le contrat que
les trois fronts consomment pour décider quoi afficher au médecin.

| Test | Ce qu'il fixe |
|---|---|
| `EnrichSync_MailServerUnreachable_Returns503ProblemJson` | 503, `Content-Type: application/problem+json`, `status`/`title`/`detail` remplis, `traceId` estampillé |
| `EnrichSync_Unreachable_LeaksNothingAboutTheMailboxOrTheServer` | le `detail` ne contient ni dossier, ni `imap`, ni `dovecot`, ni `@`, ni `Exception`, ni trace de pile |
| `EnrichSync_EverythingAlreadyAnalysed_Returns200_NotAnOutage` | le court-circuit reste un **200** — sinon le bandeau s'afficherait à chaque ouverture de dossier |
| `EnrichSync_PartialRead_Returns200_AndReportsTheAnalysedCount` | 4 analysés sur 10 dans le corps, jamais le nombre demandé |
| `ConnectionStatus_ReportsUnavailable_WhenEveryImapLinkIsDead` | `canAccessImap: false` sur la signature du banc (2 200 liens morts, 0 connecté) |
| `ConnectionStatus_ReportsAvailable_WhenLinksAreHealthy` | et `true` en régime nominal |

> ⚠️ **Un défaut de mon propre test, corrigé en cours d'écriture.** Sans
> `PscToken`, `IsOnlineMode` est faux, donc `CanAccessImap` l'est **quelles que
> soient les sessions** : le test « indisponible » passait **sans rien prouver**.
> Révélé par son jumeau « disponible », qui lui échouait — le couple valait mieux
> que le test seul.

**RED vérifié par mutation** : garde du contrôleur retirée **et** `CanAccessImap`
remis en alias d'`IsOnlineMode` ⇒ **3 des 6 tombent**, exactement les trois qui
décrivent le défaut.

**Suite** : 513 tests d'intégration (491 → 497 passés, 16 skipped), **4 513 sur
la solution**, 0 échec.


## Le point 3 retiré — tir de vérification du 2026-09-17

Arbitrage humain du 2026-09-17 : la sonde de santé sort du périmètre de
task-315. Les points 1 (503) et 2 (éviction / rétablissement) restent, **prouvés
au banc**.

### Le tir

Coupure **provoquée** du serveur de messagerie via l'API d'administration
Toxiproxy (`POST /proxies/dovecot-imap {"enabled":false}`), sous ~600 sessions,
sur la branche de la task. Le proxy est coupé, pas le serveur : Dovecot reste
vivant, maildir et UID intacts. Rétablissement armé **avant** la coupure et
indépendamment d'elle (filet à T+15 min, plus un `trap`).

| Instant | Proxy | Messages analysés | Sessions actives / connectées |
|---|---|---|---|
| 16:14:08 | ouvert | 20 270 | 616 / 616 |
| **16:14:25** | **coupé** | — | — |
| 16:14:39 | coupé | 21 584 | 617 / **310** |
| 16:15:09 | coupé | **21 584** (gelé) | 617 / **0** |
| 16:15:39 | coupé | **21 584** | **0 / 0** ← éviction |
| **16:19:25** | **rétabli** | — | — |
| 16:19:33 | ouvert | **21 589** | 1 / 1 |

### ✅ Point 1 — le 503, prouvé en conditions réelles

Pendant la coupure, sur une boîte vierge :

```
HTTP 503 en 2,21 s — application/problem+json
"La messagerie est momentanément indisponible : 5 message(s) sur 5 n'ont pas pu
 être analysés et restent à traiter. Ils le seront dès son rétablissement."
```

Ni hôte, ni dossier, ni UID. **Avant task-315, cet appel rendait 200.**

### ✅ Point 2 — l'éviction et la reprise, prouvées à l'échelle

**617 sessions mortes évincées en une minute**, sans intervention. Puis, après
rétablissement, **le même appel, la même boîte, la même session, sans redémarrer
quoi que ce soit** : `HTTP 200`, `analysed: 5`, compteur 21 584 → 21 589. Le
2026-09-16, ce même compteur est resté figé **80 minutes** et n'est jamais
reparti.

### ❌ Point 3 — la sonde ne fonctionne pas, et c'est structurel

`canAccessImap` est resté **`true` pendant toute la panne**.

**Cause établie par l'expérience.** Une tentative d'analyse pendant la coupure
laisse `active = 0` : quand la connexion ne peut pas s'établir, **aucune session
n'est retenue**. Donc `DisconnectedSessionCount = 0`, et la condition
`Disconnected > 0 && Connected == 0` n'est **jamais** vraie.

**Et le défaut n'est pas un réglage.** L'éviction des sessions mortes — celle du
point 2, qui fonctionne — **supprime exactement la preuve** que la sonde
cherchait. Les deux ne peuvent pas être vraies en même temps.

> ⚠️ **Les six tests qui gardaient ce comportement passaient tous.** Ils
> substituaient `DisconnectedSessionCount` à 2 200, une valeur que la réalité ne
> produit jamais dans ce scénario. Ils validaient le **modèle**, jamais le
> **monde**. C'est la leçon principale de ce cycle : un test qui stube la
> grandeur dont dépend tout le raisonnement ne peut pas l'infirmer.

**Retiré** : la condition dans `ConnectionModeService` (retour à
`CanAccessImap => IsOnlineMode`, aucune régression), 4 tests unitaires, 2 tests
d'intégration. `DisconnectedSessionCount` est **conservé** — il sert l'invariant
du balayage, qui lui est prouvé.

Le signal correct — **l'issue des tentatives récentes** (dernier contact IMAP
réussi, échecs consécutifs) et non l'inventaire des sessions — demande
d'instrumenter le chemin de connexion, qui n'a aujourd'hui aucun point de passage
unique. Objet d'une **US de suivi**.

**Validation après retrait** : 4 507 tests, 0 échec (−4 unitaires, −2 d'intégration).


## La cause nommée, pas seulement le statut (2026-09-17, après relecture)

Question posée à la relecture : *« si un document CDA est en échec — un ZIP
corrompu par exemple — est-ce que ça casse la chaîne de traitement ? »*

**Non**, et la vérification à la source a mis au jour autre chose.

### Ce que le code fait déjà, et qui est juste

`IheXdmProcessingService.Classify(Exception)` sépare deux familles :

| Exception | Cause | Conséquence |
|---|---|---|
| `FormatException`, `InvalidDataException`, `MimeKit.ParseException` | **`InvalidArchive`** | **le message est enregistré**, simplement sans ce document. Pas de 503, rien d'interrompu |
| `DirectoryNotFoundException` | `ScratchUnavailable` | message laissé à traiter → 503 |
| disque plein, droits, E/S | `Io` | idem → 503 |

La ligne de partage est la bonne : une archive corrompue est un **fait du
message** — la rejouer mille fois donnera mille fois le même résultat, donc la
traiter comme une panne bloquerait un praticien sur un courrier qui restera
corrompu à jamais. Un disque plein, lui, se répare.

`PersistEnrichedBatchAsync` ne teste que `HasTechnicalFailure`, qui ne compte que
`TechnicalFailureCount` : sur archive invalide le `continue` n'est pas pris, et
les autres messages du lot ne sont jamais affectés.

### Le défaut que la question a révélé

**Deux causes très différentes rendaient le même 503** sur la route d'analyse :
la messagerie injoignable (task-315) et l'extraction en échec technique
(task-293). Les trois fronts ne lisaient que le **code HTTP**. Sur une panne
d'extraction — disque, répertoire de travail — le médecin voyait donc
« Messagerie momentanément indisponible » **alors que sa messagerie
fonctionnait**, et il attendait un rétablissement sans objet.

### Le correctif

`UnavailableException` porte un code de cause, estampillé par le
`GlobalExceptionHandler` dans le champ **`code`** du `ProblemDetails` :
`MAIL_SERVER_UNAVAILABLE` / `DOCUMENT_PROCESSING_UNAVAILABLE`.

> Le `detail` distinguait **déjà** les deux cas et aurait suffi à l'œil nu. Il a
> été écarté comme discriminant : c'est une **phrase**, donc traduisible et
> reformulable. Y coupler trois fronts, c'est garantir qu'une reformulation casse
> l'affichage sans que personne ne le voie.

Les trois fronts affichent un message par cause, plus un **message neutre** quand
le serveur ne nomme pas la cause — on ne l'invente pas. Et le bandeau **reparle
si la cause change** dans un même épisode : se taire laisserait le médecin sur
une explication devenue fausse.

| Cause | Message |
|---|---|
| `MAIL_SERVER_UNAVAILABLE` | « Messagerie momentanément indisponible. Les documents seront rattachés dès son rétablissement. » |
| `DOCUMENT_PROCESSING_UNAVAILABLE` | « Traitement des documents momentanément indisponible. **Votre messagerie fonctionne** ; les documents seront analysés dès le rétablissement du service. » |
| absente | « Analyse des documents momentanément indisponible. Les documents seront rattachés dès le rétablissement du service. » |

**Tests** : 2 d'intégration backend, 9 sur la porte Blazor, 3 sur mobile, 3 sur
Angular. Dont les **contre-épreuves d'attribution** : une panne d'extraction porte
un *autre* code alors que le statut est identique. Sans elles, un code constant
passerait pour une distinction.

**Validation** : `api-mail` **4 513** · `client-blazor` **264** ·
`client-mobile` **864** · `client-angular` **382**, lint 0 erreur, `nx build mss`
vert. 0 échec.

> ⚠️ **Angle mort qui reste, et qui appartient à la US de suivi.**
> `MailListComponent.razor` (Blazor) emprunte le chemin **asynchrone**, qui rend
> `202 Accepted` immédiatement : un médecin qui ouvre un dossier pendant une panne
> **ne verra rien**, seul le widget de notifications déclenche le bandeau. Angular
> et mobile, eux, sont couverts sur l'écran principal.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/243 — label `awaiting-human-merge`
- `client-blazor` : https://github.com/codengine-technologies/HealthPlatform.Client/pull/80 — label `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/76 — label `awaiting-human-merge`
- `client-angular` : **code-only** — l'humain gère commit / push TFS et l'ouverture de la PR. Fichiers modifiés :
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.html`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.spec.ts`
  - `front/libs/mss/src/features/mail/services/mail-state.service.ts`

  ⚠️ Ils sont mêlés à **6 autres fichiers** modifiés par l'humain sur
  `feature/nova-rewriting-mss` (travail en cours, hors task-315) : trier le diff
  avant de committer.

## Code Review Summary

**APPROVED** — 4 repos, 0 blocage, 2 suggestions.

| Repo | Verdict |
|---|---|
| `api-mail` | ✅ approuvé, 2 ⚠️ sur `BackgroundImapService.cs` |
| `client-blazor` | ✅ approuvé |
| `client-mobile` | ✅ approuvé |
| `client-angular` | ✅ approuvé |

### ⚠️ Suggestions non bloquantes — toutes deux sur `BackgroundImapService.cs`

1. **`Unreachable` conflate deux causes.** Sur le chemin nominal,
   `Unreachable: pendingUids.Count - processedCount` compte aussi les UID
   **absents du serveur** (mails supprimés, retirés par `RemoveMissingUidsAsync`).
   `ImapService` garde le sien derrière `folderUnavailable ? ... : 0` ; ce
   chemin-là ne le fait pas. **Latent** — le seul appelant
   (`BackgroundSyncService:427`) ignore le résultat — mais à corriger avant que
   quiconque s'y branche, sinon un mail supprimé déclencherait une fausse
   « messagerie injoignable ».
2. **Duplication** : le littéral `new EnrichmentOutcome(uids.Count,
   alreadyEnriched.Count, 0, pendingUids.Count)` apparaît **5 fois**. La passe
   `/simplify` a factorisé exactement ce motif dans `ImapService` et a manqué
   celui-ci — l'inconsistance est de mon fait.

### Validation

| Repo | Build | Tests |
|---|---|---|
| `api-mail` | ✅ | ✅ **4 507** (183 + 492 + 2 488 + 837 + 507) |
| `client-blazor` | ✅ | ✅ **260** |
| `client-mobile` | ✅ | ✅ **861** |
| `client-angular` | ✅ `nx build mss` | ✅ **380** |

Sync `develop` : `Already up to date` sur les trois repos pushables (merge, jamais rebase — règle 4).

> ℹ️ Un commit **local non poussé** subsiste sur `api-mail/develop` :
> `f4a08b87 docs(loadtest): INDEX — les deux tirs de la campagne du 16-17/09`.
> Il n'appartient pas à task-315 (journal du banc) ; il a été laissé local pour
> ne pas déclencher le hook `verify-before-push` (build + suite complète) sur un
> changement de documentation. À pousser au prochain passage sur `develop`.

## Merged — 2026-09-17

Merge humain après validation manuelle de bout en bout (HAG, règle 10).

| Repo | Squash | PR |
|---|---|---|
| `api-mail` | `2526f413` | [#243](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/243) |
| `client-blazor` | `53b1b52` | [#80](https://github.com/codengine-technologies/HealthPlatform.Client/pull/80) |
| `client-mobile` | `1ef106f` | [#76](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/76) |
| `client-angular` | `1f901dd6` (« Task 315 ») | code-only — commit et push TFS par l'humain |

Branches `feat/task-315-messagerie-indisponible-visible` supprimées, distantes et
locales, sur les trois repos pushables. Aucune branche sur `dtos-mss` (branche
paresseuse, aucun contrat touché) ni sur `interop-cda`.

> **Règle 11 honorée** : les quatre fronts portent la US. Le commit Angular
> `1f901dd6` contient les 5 fichiers de task-315 (`problem-details.model.ts`,
> `mail-state.service.ts`, les 4 du `mail-list`) aux côtés de 5 fichiers de
> `mss-mailbox-management` appartenant au travail en cours de l'humain sur
> `feature/nova-rewriting-mss`.

### Ce qui est livré, et comment c'est prouvé

| | Preuve |
|---|---|
| `503` au lieu d'un `200` muet | **banc**, coupure provoquée du serveur sous ~600 sessions |
| Reprise sans redémarrage (compteur 21 584 → 21 589) | **banc** |
| Éviction à l'échelle (617 sessions → 0 en 1 min) | **banc** |
| Le `503` nomme sa cause (`code` du ProblemDetails) | tests, dont contre-épreuve d'attribution |
| Bandeau par cause sur les trois fronts | tests |
| Reprise en file bornée du chemin asynchrone | tests |
| Une archive invalide n'interrompt rien | lecture du code + tests task-293 |

### Ce qui reste ouvert — US de suivi

1. **La sonde de santé** (`canAccessImap`) — retirée, infirmée par le tir : quand
   la connexion ne peut pas s'établir aucune session n'est retenue, et l'éviction
   efface la preuve que la sonde cherchait. Le bon signal est l'issue des
   tentatives récentes, pas l'inventaire des sessions.
2. **Le chemin asynchrone de Blazor** — `MailListComponent.razor` emprunte
   `enrich/async`, qui rend `202` immédiatement : ouvrir un dossier pendant une
   panne n'affiche rien. Décision produit.
3. **Deux dettes dans `BackgroundImapService`** — `Unreachable` compte aussi les
   mails supprimés du serveur (latent, le seul appelant ignore le résultat), et un
   littéral d'`EnrichmentOutcome` dupliqué 5 fois que la passe `/simplify` a manqué.
