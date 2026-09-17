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
- [ ] Test unitaire : `CanAccessImap` rend `false` quand `sessions_connected == 0` et
      `sessions_active > 0` ; `true` en régime nominal
- [ ] Test d'intégration : `connection/status` reflète l'état des connexions, pas le mode
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
