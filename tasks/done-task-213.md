# todo-task-213.md — Le verrou de session IMAP est tenu 6 secondes : archiver un message envoyé attend derrière l'enrichissement en cours du même praticien

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-211 (mergée) — a posé l'instrumentation des trois verrous ;
task-205 (mergée) — a écarté la famine de ThreadPool ; le correctif d'histogrammes
`1be290d` (poussé sur `develop` le 2026-08-01) — **sans lui la mesure ci-dessous
est illisible**
**Priorité**: **2** — Instrument + expérience praticien. À instruire avant la
campagne de capacité à 500 praticiens, dont il fausse la lecture de `send`.

> **task-211 avait explicitement renvoyé cette question à une mesure**, et ne
> l'avait pas faite : « la task subordonne à la mesure la portée du verrou de
> session et l'existence du verrou en processus ». La mesure existe depuis le
> 2026-08-01. Elle désigne `imap_session`.

## Objective

Que l'archivage d'un message envoyé, et plus généralement toute opération IMAP
d'un praticien, ne fasse plus la queue pendant plusieurs secondes derrière un
enrichissement CDA en cours **du même praticien**.

**US backend-only (justification)** : portée d'un verrou applicatif dans
`ImapService` / `MailClientSessionManager`. Aucun contrat, aucun écran.

## La mesure — et pourquoi elle n'était pas lisible avant

Campagne 500 praticiens du **2026-08-01**, palier de budget 882 req/s
(`reports/2026-08-01/report-mixed-mssante-60vu-150216.md`).

| Verrou | Attente p95 | **Détention p95** | Acquisitions/s |
|---|---|---|---|
| `distributed_fetch` | 0,074 s | **6,700 s** | 7,55 |
| `imap_session` | **1,075 s** | **6,345 s** | 7,55 |
| `in_process_fetch` | 0,077 s | **7,224 s** | 7,93 |

**Les attentes sont courtes, les détentions longues.** Ce n'est donc pas une
contention sur l'acquisition — c'est **ce qui se fait sous le verrou** qui dure.
C'est exactement la lecture que task-211 avait inscrite dans le rapport : « une
attente élevée désigne la contention ; une détention élevée désigne ce qui se
fait dessous, et c'est alors sa portée qu'il faut discuter ».

Effet mesuré sur l'envoi, dans le même tir :

| `send` | valeur |
|---|---|
| médiane | **1,97 s** |
| moyenne | **6,53 s** |
| p95 | **35,1 s** |
| max | **57,5 s** |

Moyenne / médiane = **3,3**. C'est la signature de file d'attente que task-211
avait elle-même identifiée sur `read_list` (718 ms de moyenne pour 213 ms de
médiane, ratio 3,4). Un praticien sur vingt attend **plus de trente secondes**
pour envoyer un message, et le pire cas frôle la minute.

> ⚠️ **Cette table était illisible jusqu'au 2026-08-01.** Les histogrammes
> `mssante_lock_*_duration_seconds` sont libellés en secondes mais héritaient des
> bornes de buckets OpenTelemetry en **millisecondes** : 89 à 97 % des
> observations tombaient dans le premier bucket et les trois verrous publiaient
> **4,750 s à l'identique**, attente comme détention. Corrigé par `1be290d`.
> Sans ce correctif, cette US ne pouvait pas être écrite.

## Le mécanisme, établi par lecture du code

`imap_session` **sérialise toutes les opérations IMAP d'une session**, pas
seulement les lectures entre elles — le commentaire de `ImapService` le dit déjà.
Or `AppendToSentAsync` acquiert ce même verrou
(`AcquireLockAsync(userContextInfo, "AppendToSent", …)`) pour ouvrir le dossier
d'envois, y déposer le message et refermer.

Conséquence : quand un praticien envoie un message pendant qu'un enrichissement
CDA tourne sur sa boîte — le cas courant, l'enrichissement étant déclenché à la
réception — l'archivage attend la fin du fetch. Les détentions de 6 à 7 s
mesurées sur les deux verrous de fetch donnent l'ordre de grandeur de cette
attente.

## Ce qu'il ne faut PAS présumer

- **Que relâcher le verrou soit la solution.** La session IMAP MailKit **n'est
  pas thread-safe** : c'est la raison d'être du verrou, et task-211 l'avait
  explicitement laissé en place pour cela. Toute piste qui le supprime doit dire
  comment elle garantit qu'une seule commande circule à la fois sur une
  connexion donnée.
- **Que la détention de 6 s soit un défaut en soi.** Un enrichissement CDA
  *travaille* pendant ce temps (téléchargement de la pièce jointe, extraction
  IHE-XDM, parsing). Le défaut candidat est que l'archivage d'un envoi partage
  ce verrou, pas que le fetch soit lent.
- **Que le ×5,5 sur `send` mesure l'archivage.** La référence de 1,18 s avait été
  calibrée quand l'archivage **échouait instantanément** faute de dossier `Sent`
  sur le banc. Le facteur mélange donc trois choses : l'archivage devenu réel, le
  passage de 200 à 500 praticiens, et l'attente de verrou. **Les séparer fait
  partie du travail.**
- **Que `send` soit le seul chemin touché.** Toute opération IMAP du praticien
  passe par ce verrou. `send` est simplement celle où l'attente est la plus
  visible parce qu'elle est synchrone du geste du praticien.

## Contenu attendu

1. **Attribuer la détention.** Instrumenter ou exploiter l'instrumentation
   existante pour dire **quelle opération** tient `imap_session` pendant 6 s. La
   table actuelle donne une durée, pas un coupable. Sans cette attribution, tout
   correctif est un pari.
2. **Trancher la portée du verrou, et l'écrire.** Au minimum comparer :
   - **une file par praticien avec priorité** — l'archivage d'un envoi passe
     devant un enrichissement de fond, qui est asynchrone et peut attendre ;
   - **une seconde connexion IMAP dédiée aux écritures** (append `Sent` /
     `Drafts`), donc un second verrou de session, au prix d'une connexion de plus
     par praticien — à chiffrer contre le plancher `praticiens × réplicas` déjà
     documenté (2 524 sessions mesurées à 500 praticiens) ;
   - **réduire la portée de la détention** — ne tenir le verrou que le temps des
     commandes IMAP, pas pendant le parsing CDA, s'il est effectué sous le verrou.
   L'option retenue est **argumentée**, les deux autres sont **écartées par
   écrit** avec leur raison.
3. **Ne pas dégrader le cloisonnement.** Les clés de verrou portent l'isolation
   par praticien. `CrossTenantOwnershipTests` reste verte, et toute clé réécrite
   voit son test renforcé explicitement (même consigne que task-211).
4. **Rendre le gain mesurable.** La table « Verrous du chemin `read_list` » de
   `report.py` doit distinguer, après correctif, l'attente de l'archivage de
   celle du fetch — sinon on ne saura pas si le correctif a payé.

## Hors scope

- **Le coût de l'enrichissement CDA lui-même** (6-7 s de détention sur les
  verrous de fetch) — c'est du travail réel, autre sujet.
- **Les bornes de buckets des histogrammes** — corrigées par `1be290d`, rien à
  reprendre.
- **Le plafond `imap-login` du banc** (relevé le 2026-08-01 pour permettre la
  campagne 500) — propriété du banc, pas de l'application.
- **La suppression du verrou en processus** (`in_process_fetch`) — task-211 l'a
  subordonnée à la mesure ; sa détention est longue mais son **attente** est de
  77 ms, il n'est donc pas le point douloureux. À réinstruire séparément.

## Definition of Done

- [ ] Build passes (0 erreur) — Tests pass (0 échec)
- [ ] L'opération qui tient `imap_session` pendant ~6 s est **nommée**, preuve
      dans le `## Develop log`
- [ ] La portée retenue est **écrite dans le code** avec l'argument qui l'a fait
      préférer aux deux autres options, chacune écartée par écrit
- [ ] Test : un archivage d'envoi n'attend pas la fin d'un enrichissement
      concurrent du **même** praticien (test borné en temps, sur le modèle du test
      de non-blocage de task-205)
- [ ] Test : deux praticiens distincts ne partagent jamais un verrou de session
      (`CrossTenantOwnershipTests` verte, renforcée si une clé change)
- [ ] Tests **constatés RED avant le correctif** (preuve dans le `## Develop log`)
- [ ] Aucune étiquette de métrique ne porte d'email, d'INS ni de contenu de
      message (contrainte PGSSI-S + cardinalité, déjà posée par task-211)
- [ ] `report.py` distingue l'attente d'archivage de l'attente de fetch

### Dû au banc (ne bloque pas la PR, bloque la clôture de l'US)

- [ ] Tir à 500 praticiens, iso-conditions avec
      `report-mixed-mssante-60vu-150216.md` : `send` p95 **sous 10 s** et ratio
      moyenne/médiane **sous 2** (contre 35,1 s et 3,3 aujourd'hui)
- [ ] Non-régression : `read_list` et `folders_warm` p95 dans une marge de 20 %

## Manual Test Plan

1. Monter le banc en profil loadtest et seeder au moins 10 praticiens avec des
   messages porteurs de pièces jointes IHE-XDM :
   ```bash
   cd Api/Mail
   dotnet run --project src/AppHost --launch-profile https-load-test
   dotnet run --project tests/mss.mail.loadtest.seed -- --users 10 --messages 20 --api http://127.0.0.1:5052
   ```
2. **Provoquer la collision, c'est tout l'objet du test.** Sur le **même**
   praticien et le **même** `Client-Session-Id`, lancer un enrichissement de lot
   (qui dure plusieurs secondes) puis, sans attendre, un envoi :
   ```bash
   H='-H "X-Test-Bypass: loadtest-local-only" -H "Client-Email: loadtest-1@loadtest.local" -H "Client-Psc-Sub: 00000000-0000-4000-8000-000000000001" -H "Client-Rpps: 90000000001" -H "Client-Session-Id: sess-1" -H "X-PSC-Token: loadtest"'
   # enrichissement en tâche de fond (plusieurs secondes de travail réel)
   curl -s -X POST ".../api/v1/mail/folders/INBOX/emails/enrich/sync" -d '[1,2,3,4,5]' … &
   sleep 0.3
   # puis l'envoi, chronométré
   curl -s -o /dev/null -w "send=%{time_total}s\n" -X POST ".../api/v1/mail/sendmail" -d '{…}' …
   ```
3. **Ce qui doit être constaté** : avant correctif, l'envoi dure à peu près aussi
   longtemps que l'enrichissement restant (il attend le verrou). Après correctif,
   il rend la main **sans attendre la fin** de l'enrichissement.
4. Contrôle de non-régression fonctionnel : ouvrir le dossier des envois du
   praticien et vérifier que le message **y est bien archivé** — le correctif ne
   doit pas transformer l'attente en perte d'archivage :
   ```bash
   docker exec $(docker ps --filter name=loadtest-dovecot -q) \
     doveadm fetch -u loadtest-1@loadtest.local hdr.subject mailbox Sent all
   ```
5. Contrôle de cloisonnement : rejouer l'étape 2 sur deux praticiens en parallèle
   et vérifier qu'aucune boîte ne contient le message de l'autre.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — optimisation technique interne, aucune exigence
  de référencement créée ni modifiée.
- **Exigences DSR honorées** : aucune nouvelle. L'US **préserve** MSSanté-2.4
  (lecture) et le chemin d'émission, dont elle n'altère pas la sémantique.
- **INS** : non manipulée. Aucune clé de verrou ne dérive d'une INS.
- **Authentification PS** : inchangée — PSC / e-CPS, eIDAS substantiel.
- **Habilitations** : **point de vigilance repris de task-211.** Les clés de
  verrou portent le cloisonnement par praticien
  (`{email}_{ClientSessionId}`, `fetch:{email}:{folder}`). Ajouter une connexion
  ou un second verrou d'écriture crée une **nouvelle clé** : elle doit rester
  dérivée du praticien, sans quoi deux praticiens pourraient partager une
  connexion IMAP. `CrossTenantOwnershipTests` est la garde et doit rester verte.
- **Interop CI-SIS** : non applicable — aucun format d'échange touché. Le contenu
  archivé est le message déjà émis, inchangé.
- **Tracé PGSSI-S** : aucun **nouvel** évènement métier. L'instrumentation produit
  des **métriques techniques** (durées de verrou, issue d'acquisition) sans
  donnée de santé ni identifiant patient. Durée de conservation inchangée.
  ⚠️ L'archivage dans le dossier d'envois est la **trace métier** de
  l'émission côté praticien : un correctif qui le rendrait « au mieux » (perte
  silencieuse possible) dégraderait l'imputabilité. C'est pourquoi le DOD exige
  la vérification d'archivage effectif, pas seulement la latence.
- **Consentement patient** : non applicable — aucun partage nouveau.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : non — banc de charge, données 100 % synthétiques
  (boîtes `loadtest-*`, pièces jointes du corpus de test).
- **AIPD / impact RGPD** : inchangé — aucune nouvelle donnée collectée ni
  nouvelle finalité.

## Branches
- `api-mail` (pushed) : fix/task-213-imap-session-lock-scope — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-213-imap-session-lock-scope
- `dtos-mss` (pushed, auto-inclus) : fix/task-213-imap-session-lock-scope — aucun contrat attendu (US backend-only)

## Develop log

### L'opération qui tient `imap_session` — nommée (DOD 1)

**`EnrichEmails`**, phase A. Établi par lecture du code : task-079 a scindé
l'enrichissement et sort déjà la persistance et le parsing CDA du verrou
(`ImapService.EnrichEmailsAsync`, commentaire « Phase A / Phase B ») ; ce qui
reste sous le verrou est le fetch réseau des corps et pièces jointes du lot,
boucle `FetchMailBodiesAsync` sur les UID du lot. C'est du travail réel — la
task le place hors périmètre.

La preuve **chiffrée** exigera le banc : la table de task-211 agrège sur le
verrou et ne peut pas nommer l'opération. C'est l'objet de l'étiquette
`operation` ajoutée ici.

### Tests constatés RED avant le correctif (DOD 6)

`dotnet build tests/mss.mail.application.tests` avant implémentation :

```
WriteLaneSessionTests.cs(110,55): error CS1061: 'UserContextInfo' ne contient pas
  de définition pour 'ForWriteLane' …   (× 4 sites)
WriteLaneSessionTests.cs(188,44): 'MailProcessingMetrics' ne contient pas de
  définition pour 'LockOperationFamily'
```

Après implémentation : **10/10 verts**.

### Correction de l'énoncé — l'option 3 était déjà livrée

L'énoncé proposait de « ne tenir le verrou que le temps des commandes IMAP, pas
pendant le parsing CDA, **s'il est effectué sous le verrou** ». Il ne l'est pas :
task-079 l'a sorti. Cette option est donc **sans objet**, et c'est écrit comme
telle dans `UserContextInfo.ForWriteLane`.

### Réserve reportée au HAG

Le ×5,5 sur `send` mélange trois causes (archivage devenu réel, 200 → 500
praticiens, attente de verrou) — la task le dit et cette PR ne traite que la
troisième. La nouvelle table par opération est ce qui permettra de les séparer.

## Sonar log

**0 issue** sur les 6 fichiers C# touchés et sur les 2 nouveaux fichiers de test.
Les 3 `python:S3776` de `report.py` sont pré-existants — `reduce_prom_matrix`,
`pinned_candidates`, `_observe_table` (task-204 et PR #135) ; la nouvelle
fonction `_session_lock_operation_table` n'en fait pas partie.

> ⚠️ KPIs projet toujours inexploitables — cf. `## Sonar log` de task-212,
> `agents/sonar.md` à corriger et baseline à refaire.

## PRs
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/140 — label `awaiting-human-merge`
- `dtos-mss` : aucune PR — branche sans commit (US backend-only)

## Code Review Summary

**APPROVED** — 11 fichiers, 0 blocage.

- `UserContextInfo.ForWriteLane` — ✅ clone par `MemberwiseClone` (aucun champ
  oubliable au fil des évolutions) ; l'arbitrage complet et les deux options
  écartées y sont écrits.
- `MailProcessingMetrics.LockOperationFamily` — ✅ borne la cardinalité **et**
  coupe la fuite : `GetAttachment` concatène le nom de la pièce jointe.
- `MailClientSessionManager` — ✅ les trois points de mesure étiquetés, aucune
  autre sémantique touchée.
- `ImapConnectionService` — ✅ surcharge à contexte explicite, l'ancienne délègue.
- `ImapService` — ✅ voie d'écriture centralisée sur une propriété ; les autres
  opérations de brouillon restent sur la voie de lecture, justifié sur place.
- `report.py` — ✅ table rendue même vide, et **ligne de verdict** qui confronte
  l'archivage au reste plutôt que de laisser la conclusion au lecteur.

### Ajustements de tests existants
9 tests ajustés : leurs substituts stubbaient l'ancienne surcharge de connexion.
**Aucune assertion comportementale modifiée** — les deux voies sont désormais
stubbées séparément pour que `DeleteDraft`, resté sur la voie de lecture,
continue de le prouver.

### Observations non bloquantes
- Deux flakies pré-existants sont apparus une fois sur quatre exécutions de la
  suite complète (`MailExportServiceTests` / `MarkdownPdfRendererTests`, état
  statique PdfPig ; `FlagsmithFeatureFlagServiceTests.RefreshFailure…`,
  `MeterListener` global). Verts en isolation, et la dernière suite complète est
  à **3 280 verts, 0 échec**. Aucun lien avec ce diff.
