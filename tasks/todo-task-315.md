# todo-task-315.md — Une indisponibilité de la messagerie cesse d'être silencieuse : l'analyse rend un résultat, les sessions se rétablissent, la santé dit la vérité

**Repos**: api-mail
**Dependencies**: — (aucune ; n'entre en conflit avec aucune US en vol)
**Epic**: E015
**Single frontend**: true
**Priorité**: **1** — **perte de donnée médicale silencieuse**, du même ordre que
`task-196` et `task-290`. Pendant 80 minutes, l'application a répondu « ✅ analysé »
à chaque demande **sans écrire un seul document dans un dossier patient**, et rien —
ni log d'erreur, ni métrique, ni sonde de santé — ne l'a signalé.

> **Origine** : campagne de charge du 2026-09-16/17, palier 1000 (passe d'hydratation).
> Rapport : `Docs/audits/api-mail-loadtest-journey-500-audit-basecommune-20260917.md`.
> Cause **mesurée puis lue dans le code**, pas supposée.

## Objective

Qu'une indisponibilité du serveur de messagerie **se voie** — dans la réponse HTTP, dans
les journaux, dans les métriques et dans la sonde de santé — et que l'application **s'en
remette d'elle-même** au lieu de rester bloquée jusqu'au prochain redémarrage.

Trois changements indissociables : le premier rend l'échec observable, le deuxième le
rend transitoire, le troisième le rend détectable de l'extérieur. Livrer le premier seul
donnerait une erreur qu'on ne sait pas guérir ; le deuxième seul guérirait une panne
qu'on ne sait toujours pas voir.

## Ce qui a été mesuré — tir `journey-1000-hydratation-20260916`, 3 h 30 à 1000 médecins

| Grandeur | t+120 min | t+130 min | t+210 min (fin) |
|---|---|---|---|
| Messages analysés (`mssante_enrichment_message_duration_seconds_count`, brut) | 71 205 | **72 101** | **72 101** |
| Requêtes HTTP servies (cumul) | 676 982 | 769 094 | **1 721 672** |
| Sessions IMAP **actives** (`mssante_imap_sessions_active`) | 2 224 | 1 511 | 2 177 |
| Sessions IMAP **connectées** (`mssante_imap_sessions_connected`) | 2 224 | **0** | **0** |
| Réplicas exportant leurs métriques | 5 | 5 | 5 |

**Le compteur d'analyse est gelé pendant 80 minutes** alors que l'application sert
**950 000 requêtes de plus** et que les cinq réplicas publient toujours : ce n'est ni un
trou d'instrumentation, ni une machine saturée, ni une décroissance progressive. C'est un
arrêt net, à la minute où **toutes** les sessions IMAP passent de connectées à zéro.

Sur la même période, `POST …/emails/enrich/sync` **continue d'être appelé au même rythme**
(≈ 4 250 requêtes par tranche de 20 min) et répond **`HTTP 200`, zéro erreur**, en **2 à
3 secondes** — donc ce n'est pas le court-circuit « déjà analysé », qui répond en ~25 ms.
Contrôle nominatif dans Seq : `loadtest-815` appelle `enrich/sync` à t+170 min, reçoit
`200` en 2 334 ms, et **termine le tir avec `MailContents = 0`**. Vérifié en base :
l'hydratation est pleine jusqu'à l'index ~640, dégradée jusqu'à ~700, **nulle au-delà** —
72 101 ÷ 98 messages par médecin ≈ 736 médecins, exactement le front observé.

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

Trois défauts empilés, chacun corrigeable séparément :

1. **`EnrichEmailsAsync` rend `Task`.** Le contrôleur n'a aucun moyen de savoir combien
   de messages ont été analysés. Il journalise `uids.Count` — le nombre **demandé**,
   jamais le nombre **traité**. Les trois interfaces concernées (`IImapService`,
   `IImapEmailFetchService`, `IBackgroundImapService`) portent la même signature muette.
2. **`FolderUnavailable` est une information que le code possède et jette.**
   `SingleMailFetch` et `EnrichmentChunkFetch` la transportent jusqu'à la boucle, qui
   s'en sert pour sortir — puis la perd.
3. **La sonde de santé ne consulte pas les connexions.**
   `ConnectionModeService.CanAccessImap => IsOnlineMode` : un drapeau de mode, pas un
   état. Pendant toute la panne, `GET /api/v1/connection/status` a répondu
   `{"mode":"online","canAccessImap":true}`.

> ⚠️ **Ce n'est PAS un problème de file d'attente.** Le chemin
> `enrich/sync → ImapService.EnrichEmailsAsync` est **entièrement synchrone** : aucun bus,
> aucune queue. Une file ajoutée ici sans les correctifs ci-dessous reproduirait la même
> panne avec une indirection de plus. La reprise par file est une piste **ultérieure**
> (les UID non traités restent déjà `pending` — cf. le commentaire de `ImapService.cs:1398`).

## Portée — les trois changements

### 1. L'analyse rend un résultat, et l'échec devient une erreur typée

`EnrichEmailsAsync` rend un résultat porteur de quatre comptes : **demandés**, **déjà
analysés** (court-circuit), **analysés**, **non joignables**. Les trois interfaces sont
alignées.

Le contrôleur en tire son comportement :

- au moins un message analysé, ou tous déjà analysés ⇒ **`200`**, avec le compte réel
  dans le corps de la réponse **et** dans le log (`✅ Enriched {Analysed}/{Requested}`) ;
- **aucun message analysé alors qu'il en restait à traiter, parce que la messagerie n'est
  pas joignable** ⇒ **`503`** via `UnavailableException`, donc `ProblemDetails` RFC 7807
  produit par le `GlobalExceptionHandler` — **règle 12 du CLAUDE.md, non négociable**.
  Aucun `try/catch` ad hoc dans l'action, aucun `StatusCode(503, "...")`.

Le `detail` exposé au client nomme l'indisponibilité, **jamais** le serveur IMAP, son
hôte, le nom du dossier, un UID ni un fragment de message.

### 2. Une session dont la connexion est perdue se rétablit ou disparaît

Aujourd'hui, 2 200 sessions sont restées **actives sans être connectées pendant
80 minutes**, sans jamais être ni reconnectées ni évincées. Après cette US :

- une session dont le lien IMAP est tombé est **reconnectée au prochain usage**, ou
  **évincée du pool** si la reconnexion échoue — jamais conservée dans un état inutilisable ;
- l'éviction et la reconnexion sont **journalisées** et **comptées** (nouveau compteur),
  pour qu'une tempête de reconnexions soit lisible au lieu d'être déduite ;
- le rétablissement ne dépend d'**aucun** redémarrage de réplica.

### 3. La santé reflète les connexions réelles

`CanAccessImap` cesse d'être un alias d'`IsOnlineMode`. `GET /api/v1/connection/status`
rend `canAccessImap: false` quand le compte de sessions **connectées** est nul alors que
des sessions **actives** existent — c'est-à-dire exactement la signature mesurée.

## Definition of Done

- [ ] Build passe sur `api-mail` (0 erreur) ; tests passent (0 échec)
- [ ] `EnrichEmailsAsync` rend un résultat à quatre comptes (demandés / déjà analysés /
      analysés / non joignables) ; les trois interfaces `IImapService`,
      `IImapEmailFetchService`, `IBackgroundImapService` sont alignées
- [ ] **Test unitaire — LE CAS DU 2026-09-16** : `FolderUnavailable` sur le premier
      sous-lot, aucun message lu, des UID restant à traiter ⇒ `UnavailableException`
      levée. Ce test doit **échouer** sur le code actuel
- [ ] Test unitaire : lot entièrement déjà analysé ⇒ **`200`**, `Analysed=0`,
      `AlreadyAnalysed=N`, **aucune** exception — le court-circuit n'est pas une panne
- [ ] Test unitaire : lot partiellement lu (indisponibilité au 3ᵉ sous-lot) ⇒ **`200`**,
      le travail déjà payé est persisté, les UID non traités restent `pending`
- [ ] Test d'intégration : `POST …/emails/enrich/sync` messagerie injoignable ⇒ **`503`**
      en `application/problem+json`, `title`/`detail`/`status` conformes RFC 7807,
      produit par le `GlobalExceptionHandler` (règle 12)
- [ ] **Test de non-fuite (bloquant)** : le `detail` du `ProblemDetails` ne contient ni
      hôte IMAP, ni nom de dossier, ni UID, ni INS/NIR, ni fragment de contenu MSSanté/CDA
- [ ] Le log de succès porte le nombre **analysé**, plus jamais le nombre **demandé** ;
      un test le vérifie sur un lot partiellement traité
- [ ] Test unitaire : une session dont le lien IMAP est tombé est **reconnectée** au
      prochain usage ; si la reconnexion échoue, elle est **évincée** du pool
- [ ] Test unitaire : aucune session ne peut rester `active` et non `connected` au-delà
      d'un usage — c'est l'inversion exacte du défaut mesuré
- [ ] Compteurs exposés **et exportés** (`AddMeter` vérifié — cf. F-297-M) : reconnexions
      tentées, reconnexions échouées, sessions évincées, messages non joignables
- [ ] Test unitaire : `CanAccessImap` rend `false` quand `sessions_connected == 0` et
      `sessions_active > 0` ; `true` en régime nominal
- [ ] Test d'intégration : `GET /api/v1/connection/status` reflète l'état des connexions
      et non le seul mode
- [ ] Aucune donnée de santé en clair dans les logs ajoutés
- [ ] Évènements PGSSI-S journalisés : indisponibilité de la messagerie constatée,
      reconnexion, éviction de session

## Manual Test Plan

**Lancer le banc** (profil loadtest, serveurs mail locaux — pas besoin du cluster) :

```bash
cd Api/Mail
taskkill /F /IM dcp.exe /T 2>/dev/null
rm -rf ~/.dcp/state.elevated ~/.dcp/mruPorts.elevated.list
dotnet run --project src/AppHost --launch-profile https-load-test
dotnet run --project tests/mss.mail.loadtest.seed -- --users 3 --messages 20 \
  --api http://127.0.0.1:5052 \
  --registry "Host=127.0.0.1;Port=5432;Username=postgres;Password=postgres;Database=mss_registry_loadtest"
```

⚠️ Le registre de banc doit être **une base dédiée** : le seed refuse d'écrire dans un
registre portant un compte hors banc (constaté le 2026-09-16 sur `mss_registry`).

**Étape 1 — nominal.** Analyser un lot sur une boîte vierge :

```bash
curl -i -X POST "http://127.0.0.1:5052/api/v1/mail/folders/INBOX/emails/enrich/sync" \
  -H "Content-Type: application/json" -H "X-Test-Bypass: loadtest-local-only" \
  -H "Client-Email: loadtest-1@loadtest.local" \
  -H "Client-Psc-Sub: 00000000-0000-4000-8000-000000000001" \
  -H "Client-Rpps: 90000000001" -H "Client-Session-Id: sess-1" -H "X-PSC-Token: loadtest" \
  -d '[1,2,3,4,5]'
```

**Attendu** : `200`, et le corps indique **5 analysés**. Le log console porte
`✅ Enriched 5/5`.

**Étape 2 — le même lot une seconde fois.** Rejouer la commande identique.
**Attendu** : `200`, **0 analysé, 5 déjà analysés**. Pas d'erreur : redemander l'analyse
de ce qui est déjà fait n'est pas une panne.

**Étape 3 — LE CAS DU DÉFAUT.** Couper le serveur IMAP pendant que la session vit :

```bash
docker stop $(docker ps --filter name=loadtest-dovecot --format '{{.Names}}')
```

Puis relancer la commande de l'étape 1 sur les UID **6 à 10** (jamais analysés).

**Attendu, et c'est le cœur de la US** :
- **`503`**, `Content-Type: application/problem+json`, corps RFC 7807 annonçant
  l'indisponibilité de la messagerie ;
- **aucune** mention d'hôte IMAP, de dossier, d'UID ou de contenu dans le `detail` ;
- **aucun** `✅ Enriched` dans les logs.

*Avant cette US, cet appel rend `200` et le log affiche `✅ Enriched 5 UIDs`.*

**Étape 4 — la santé le dit.**

```bash
curl -s "http://127.0.0.1:5052/api/v1/connection/status" -H "X-Test-Bypass: loadtest-local-only" \
  -H "Client-Email: loadtest-1@loadtest.local" \
  -H "Client-Psc-Sub: 00000000-0000-4000-8000-000000000001" \
  -H "Client-Rpps: 90000000001" -H "X-PSC-Token: loadtest"
```

**Attendu** : `canAccessImap: false`.
*Avant cette US : `{"mode":"online","canAccessImap":true}` — en pleine panne.*

**Étape 5 — le rétablissement, sans redémarrage.**

```bash
docker start $(docker ps -a --filter name=loadtest-dovecot --format '{{.Names}}')
```

Attendre que le conteneur soit prêt, puis **rejouer l'étape 3 telle quelle**, **sans
redémarrer l'AppHost ni aucun réplica**.

**Attendu** : `200`, **5 analysés**. La sonde de l'étape 4 rend de nouveau
`canAccessImap: true`.
*Avant cette US : l'analyse restait à zéro indéfiniment — 80 minutes mesurées au banc,
sans reprise.*

**Étape 6 — la preuve en base.** Vérifier que les messages sont bien arrivés :

```bash
docker exec postgres-pgvector psql -U postgres \
  -d $(docker exec postgres-pgvector psql -U postgres -tAc \
       "select datname from pg_database where datname like 'u\_90000000001\_%' limit 1" | tr -d ' ') \
  -tAc 'select count(*) from "MailContents"'
```

**Attendu** : 10 (les 5 de l'étape 1 + les 5 de l'étape 5). **C'est ce contrôle-là qui
tranche** : au banc, l'API annonçait des succès pendant que ce compte restait à 0.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors vague — correctif de robustesse sur une fonction existante,
  n'introduit aucune exigence DSR nouvelle
- **Exigences DSR honorées** : aucune nouvelle. La US **protège** l'alimentation du
  dossier patient par documents CDA reçus en MSSanté, déjà couverte par l'existant
- **INS** : non applicable — la US ne touche ni au calcul, ni au statut, ni au
  rapprochement de l'INS. Elle garantit seulement que les documents qui portent une INS
  **arrivent effectivement** jusqu'au rapprochement, au lieu d'être perdus en silence
- **Authentification PS** : inchangée — PSC / e-CPS, niveau eIDAS substantiel. Aucun
  chemin d'authentification modifié
- **Habilitations** : inchangées — RPPS porté par le contexte utilisateur existant
- **Interop CI-SIS** : CDA r2 — **format inchangé**. La US porte sur la fiabilité de
  l'acheminement vers l'analyse, pas sur le contenu ni sur le parsing
- **Tracé PGSSI-S** : trois évènements ajoutés — *indisponibilité de la messagerie
  constatée lors d'une analyse*, *reconnexion de session*, *éviction de session*.
  Conservation alignée sur les traces techniques existantes (365 jours,
  `AuditRetentionPolicy`). Aucun de ces évènements ne porte de donnée de santé
- **Consentement patient** : non applicable — aucun partage, aucune publication DMP /
  Mon Espace Santé introduits
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — le chemin concerné manipule des DSCP (corps de messages
  MSSanté et documents CDA). Aucune nouvelle donnée n'est créée, stockée ni transmise
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau, aucune donnée
  supplémentaire collectée. La US **réduit** un risque d'intégrité : des documents
  médicaux qui n'entraient jamais dans le dossier sans que personne en soit informé

## Ce que cette US ne fait pas

- **Elle ne met pas l'analyse en file d'attente.** Le chemin reste synchrone ; la reprise
  par travailleur de plateforme est un chantier distinct, à instruire **après** celui-ci.
- **Elle ne cherche pas pourquoi les sessions se sont déconnectées** le 2026-09-16.
  L'hypothèse — redémarrage du pod Dovecot/Toxiproxy du cluster — n'est pas vérifiable
  depuis ce poste (`kubectl` refusé), et **elle n'a pas besoin de l'être** : quelle que
  soit la cause de la déconnexion, l'application doit la voir et s'en remettre.
- **Elle ne corrige pas la chauffe du banc** (`journey_warmup_completed` valait 1,0 alors
  que 264 médecins n'avaient rien reçu). C'est un finding de harnais séparé : la chauffe
  doit se vérifier en base, pas au code HTTP.
