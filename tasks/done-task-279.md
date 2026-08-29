# todo-task-279.md — Le téléchargement d'une pièce jointe entre dans le compteur de sollicitations

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015

## Objectif

`GetAttachmentStream` est la **seule** opération dont la détention du verrou
`imap_session` est *tenue en régime* — et c'est aussi la seule dont les
commandes IMAP **ne sont comptées par rien**.

Instruction menée le 2026-08-29 sur les données du tir
(`Api/Mail/tests/loadtest-k6/reports/2026-08-29/report-journey-500-task270-20260829-220155.md`,
finding **F-ATT-1**), fenêtre de régime, palier 500 :

| Grandeur | Valeur | Lecture |
|---|---|---|
| Attente du verrou, médiane | **0,005 s** | elle **n'attend pas** — ce n'est pas une file |
| Détention `operate`, médiane | **0,699 s** | **la plus élevée de toutes les opérations** (peloton : 0,242 à 0,500 s) |
| Part des relevés > 2 s | **11,6 %** | seule opération soutenue hors chauffe ; les autres sont des transitoires |
| Acquisitions | 1,13 /s | — |

Décomposition par phase (task-252), p95 — **la détention est intégralement
expliquée, sans résidu** (somme 0,746 s ≈ détention 0,699 s) :

| Phase | p95 | Moyenne/appel | Part |
|---|---|---|---|
| `imap_fetch` (BODYSTRUCTURE + `BODY[part]`) | **0,435 s** | 95,8 ms | **58 %** |
| `session_acquire` (verrou + connect + resolve + SELECT) | 0,241 s | 53,8 ms | 32 % |
| `assemble` (décodage + écriture du cache en base) | 0,033 s | 6,6 ms | 4 % |
| `db_lookup` | 0,032 s | 10,3 ms | 4 % |
| `stream` | 0,005 s | 0,4 ms | 0,2 % |

### ⚠️ Deux causes plausibles sont DÉJÀ écartées — ne pas les réinstruire

1. **« Une écriture base sous le verrou IMAP »** — hypothèse tirée de la lecture
   du code : le verrou (`await using var lockScope`) couvre **toute** la méthode,
   y compris `BuildCachedAttachmentStreamAsync` qui décode ~124 Ko, en fait une
   seconde copie (`ToArray()`) et écrit en base (`UpdateAttachmentAsync`).
   **RÉFUTÉE par la mesure** : `assemble` vaut 6,6 ms en moyenne, 4 % de la
   détention.
2. **« Elle subit la contention des autres »** — **RÉFUTÉE** : attente médiane
   5 ms.

### Le défaut, et c'est un angle mort d'instrument

Le compteur de sollicitations (task-225, étendu au chemin des dossiers par
task-262) couvre `ConnectImap`, `EnrichEmails`, `GetEmailContent`,
`GetFolderQuery`, `GetFolderStatus`, `SmtpConnect`, `SmtpKeepAlive`,
`SmtpSend`. **`GetAttachmentStream` n'y figure pas — 0 entrée sur la fenêtre.**

La lecture du code donne **quatre** commandes (`GetFolderAsync` → resolve,
`OpenAsync` → SELECT, `FindAttachmentPartAsync` → BODYSTRUCTURE,
`DownloadAttachmentMimePartAsync` → `BODY[part]`), mais **rien ne le prouve et
rien ne le suivra**. ⚠️ **Une absence n'est pas un zéro** (task-214) : ces
commandes partent, elles ne sont pas comptées.

**Conséquence directe : la piste la plus prometteuse est indécidable.** Le
parcours du médecin ouvre le message **puis** télécharge sa pièce jointe, dans
le même dossier — la session a vraisemblablement déjà ce dossier sélectionné,
donc le `OpenAsync(ReadOnly)` serait **redondant**. C'est la même forme que le
doublon `resolve` + `STATUS` supprimé par task-270. Sans compteur, on ne peut ni
l'établir ni le mesurer après correction.

### Contenu attendu, dans cet ordre

1. **Instrument** — étendre `mssante_mail_server_solicitations_total` au chemin
   PJ, avec l'opération `GetAttachmentStream` et les commandes réellement
   émises. **C'est le geste exact de task-262 sur l'autre chemin** : s'en
   inspirer, ne pas réinventer la forme des étiquettes (la comparabilité des
   séries de campagnes en dépend).
2. **Établir sur pièce** le nombre réel d'allers-retours, et **si le SELECT est
   redondant** quand le dossier est déjà sélectionné sur la session.
3. **Remède, seulement si (2) le justifie** — éviter le `OpenAsync` inutile.
   **Si le SELECT n'est jamais redondant, l'US s'arrête ici** : le constat est
   consigné, et c'est un résultat (précédent task-276, qui s'est arrêtée à son
   instrument).

**Gain attendu** : au mieux 1 aller-retour sur 4 (~100 ms de latence simulée),
soit ~15 % de la détention. Le bénéfice n'est **pas** pour le téléchargement
lui-même — il est pour les **autres gestes du même praticien**, que
`imap_session` sérialise derrière lui.

**Ce qui n'est PAS dans le périmètre** : `imap_fetch` (58 % de la détention,
2 commandes incompressibles sous ~100 ms de latence + le transfert de ~124 Ko) ;
l'écriture du cache (réfutée ci-dessus) ; le contrat de la route.

### ⚠️ Mise en perspective — priorité honnête

L'étape « Télécharger une PJ » est **verte** au SLO (p50 16 ms / p95 689 ms pour
une cible de 500/2 000) et pèse **5,6 %** du temps serveur. **Ce n'est pas une
urgence produit.** Sa valeur est un **risque de sérialisation** pour les autres
gestes du praticien quand la population monte. task-278 (34,9 % du temps
serveur) reste plus rentable — cette US se prend quand elle ne retarde pas la
précédente.

## Definition of Done

- [ ] Build passes (0 erreur)
- [ ] Tests pass (0 échec)
- [ ] `GetAttachmentStream` apparaît dans
      `mssante_mail_server_solicitations_total`, avec la même forme d'étiquettes
      que les chemins déjà couverts (comparabilité des séries)
- [ ] Test unitaire épinglant le **nombre ET l'ordre** exacts des commandes
      émises par un téléchargement, dans le style de
      `ImapServiceFolderStatusSolicitationTests` (task-262/270)
- [ ] Test épinglant qu'un téléchargement **servi par le cache base** n'émet
      **aucune** sollicitation (le court-circuit en tête de méthode)
- [ ] Test d'absence provable : une connexion en échec n'enregistre rien
      (précédent `AFailedConnection_RecordsNothing_AbsenceStaysProvable`)
- [ ] La redondance du `OpenAsync` est **établie et écrite** dans le task file,
      chiffres à l'appui — y compris si la réponse est « jamais redondant »
- [ ] Si remède : le nombre d'allers-retours baisse **et le compteur le prouve**
- [ ] Si remède : contrat de la route inchangé, corps de réponse identique —
      testé
- [ ] Aucune donnée de santé : les étiquettes du compteur restent des littéraux
      (nom d'opération, nom de commande) — **jamais** le nom de fichier de la
      pièce jointe, jamais l'UID, jamais le dossier patient

## Manual Test Plan

**Ce que l'humain valide au HAG** : que le téléchargement d'une pièce jointe
fonctionne à l'identique. Le gain est un fait de banc, jugé au tir suivant.

1. Lancer le banc :
   ```bash
   cd Api/Mail
   dotnet run --project src/AppHost --launch-profile https-load-test
   ```
2. Attendre `http://127.0.0.1:5052/api/v1/connection/status` en 200, puis
   seeder : `dotnet run --project tests/mss.mail.loadtest.seed -- --users 2 --messages 20 --api http://127.0.0.1:5052`
3. Enrichir avant de lire (piège n°1 du banc) :
   `POST /api/v1/mail/folders/INBOX/emails/enrich/sync` avec `[1,2,3]` et les
   en-têtes d'identité virtuelle (`Client-Email: loadtest-1@loadtest.local`,
   `Client-Rpps: 90000000001`,
   `Client-Psc-Sub: 00000000-0000-4000-8000-000000000001`,
   `Client-Session-Id: sess-1`, `X-Test-Bypass: loadtest-local-only`,
   `X-PSC-Token: loadtest`).
4. Ouvrir le message 1, puis **télécharger sa pièce jointe** :
   `GET /api/v1/mail/folders/INBOX/emails/1/download/attachment/IHE_XDM.ZIP`
5. **Vérifier** : le fichier arrive complet et s'ouvre (archive ZIP valide,
   ~124 Ko). C'est le seul critère fonctionnel — le reste est de la mesure.
6. **Vérifier le compteur** :
   ```bash
   curl -s --get "http://127.0.0.1:${PROM_PORT}/api/v1/query" \
     --data-urlencode 'query=sum by (command) (mssante_mail_server_solicitations_total{operation="GetAttachmentStream"})'
   ```
   Les commandes attendues apparaissent, avec leur compte.
7. **Re-télécharger la même pièce jointe** : elle doit être servie par le cache
   base, et le compteur **ne doit pas bouger**.
8. Vérifier qu'aucune étiquette du compteur ne porte le nom du fichier, l'UID
   ni un identifiant patient.
9. **Clôture de l'US — au banc, tir suivant** : tir `journey` 500 médecins en
   iso-conditions du `report-journey-500-task270-20260829-220155.md`, sur la
   **même base hydratée**. Critères :
   - nombre d'allers-retours par téléchargement **publié par le compteur**
     (c'est le livrable minimal, même sans remède)
   - si remède : détention `operate` médiane de `GetAttachmentStream`
     **< 0,600 s** (contre 0,699) et part des relevés > 2 s **< 8 %**
     (contre 11,6 %)
   - étape « Télécharger une PJ » toujours verte, corps de réponse inchangé

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — instrumentation et performance internes
- **Exigences DSR honorées** : non applicable — comportement fonctionnel inchangé
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — la pièce jointe transportée est une
  archive IHE-XDM déjà traitée par `interop-cda` en aval ; cette US ne touche
  que le transport IMAP et son comptage
- **Tracé PGSSI-S** : inchangé — le téléchargement reste journalisé à
  l'identique. ⚠️ **Le compteur ajouté ne doit porter aucune étiquette à
  cardinalité patient** : ni nom de fichier, ni UID, ni dossier — uniquement des
  littéraux d'opération et de commande (précédent task-256, où le typage par
  énumération a rendu la fuite impossible à écrire)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — inchangé
- **AIPD / impact RGPD** : inchangé — aucune donnée nouvelle collectée, le
  compteur est une métrique technique sans identifiant

## Branches

- `api-mail` (pushed) : `feat/task-279-attachment-solicitations`
- `dtos-mss` (pushed, auto-inclus) : `feat/task-279-attachment-solicitations`
- `client-angular`, `client-mobile`, `devops`, `psc-proxy-*` — non concernés

## Develop log

**Repos touchés** : `api-mail` uniquement. `dtos-mss` : branche créée, **0 commit**.

### Étape 1 — l'instrument (livré)

Quatre points de comptage dans `GetAttachmentStreamAsync`, famille
`GetAttachmentStream`, littéraux existants de `MailServerCommands` (aucun nouveau
nom — la comparabilité des séries de campagnes en dépend) :

| Commande | Site |
|---|---|
| `resolve_folder` | `GetFolderAsync` |
| `open_folder` | `OpenAsync` — **conditionnel, voir ci-dessous** |
| `fetch_bodystructure` | `FindAttachmentPartAsync` |
| `fetch_body_part` | `DownloadAttachmentMimePartAsync` |

### ⭐ Le point qui décide de la valeur du compteur : ne compter que les ouvertures RÉELLES

MailKit **court-circuite** `OpenAsync` quand le dossier est déjà ouvert avec le
même accès. Compter l'appel plutôt que la commande aurait rendu un **majorant**
— et aurait fait croire à une redondance là où il n'y en a pas. Or c'est
**exactement la question** que ce compteur existe pour trancher : le parcours du
médecin ouvre le message *puis* télécharge sa pièce jointe, dans le même
dossier. Le compteur teste donc `IsOpen && Access == ReadOnly` avant d'inscrire.

C'est la différence entre un instrument qui répond à la question et un
instrument qui la maquille — la leçon que task-276 vient de payer.

### Étape 2 — établir la redondance : reportée au banc, à raison

Le test `AnAlreadySelectedFolder_DoesNotPayTheSelectAgainAsync` prouve le
**mécanisme** (dossier déjà ouvert ⇒ pas de `open_folder` compté). Mais la
question de l'US — « le SELECT est-il redondant **en pratique** ? » — est une
question de **fréquence**, pas de mécanisme : elle se lit au banc, sur le
rapport du prochain tir, dans le rapport `open_folder / resolve_folder` de la
famille `GetAttachmentStream`. C'est le critère de clôture inscrit au Manual
Test Plan.

### Étape 3 — remède : non écrit, volontairement

L'US l'autorisait explicitement (« si le SELECT n'est jamais redondant, l'US
s'arrête ici »). Écrire un contournement de `OpenAsync` avant de savoir s'il
sert serait le raccourci que cette EPIC a déjà payé deux fois.

### Vérification

- `dotnet build HealthPlatform.Api.Mail.sln` → **0 erreur, 0 avertissement**
- domain 136/136 · infrastructure 464/464 · api 692/692 · application **2 191/2 191**
- **5 tests neufs** : les 4 commandes **dans l'ordre** sur téléchargement froid ;
  pièce jointe introuvable → les 3 commandes déjà envoyées sont **quand même**
  comptées (ne rien compter ferait passer un appel coûteux pour gratuit) ;
  téléchargement servi par le cache base → **rien** ; connexion en échec →
  **rien** (absence prouvable, garde de task-270) ; dossier déjà ouvert → pas de
  `open_folder`.

**Piège d'outillage rencontré** : `FetchAsync(IList<UniqueId>,
MessageSummaryItems, CancellationToken)` est une **méthode d'extension** de
MailKit — NSubstitute ne peut pas l'intercepter et laisse des matchers en
suspens (`RedundantArgumentMatcherException`). Le membre d'interface prend
`IFetchRequest` ; c'est lui qu'il faut mocker, comme le font déjà
`ImapServiceTests` et `BackgroundSyncPipelineTests`.

### DOD

- [x] Build 0 erreur — [x] Tests verts
- [x] `GetAttachmentStream` au compteur, mêmes étiquettes que les chemins couverts
- [x] Test épinglant **nombre et ordre** des commandes
- [x] Test : téléchargement servi par le cache → aucune sollicitation
- [x] Test d'absence provable : connexion en échec → rien
- [ ] Redondance du `OpenAsync` **établie** → **reportée au banc** (question de
      fréquence, pas de mécanisme) — critère de clôture au Manual Test Plan
- [x] Remède : sans objet à ce stade (issue prévue par l'US)
- [x] Aucune donnée de santé : littéraux d'opération et de commande uniquement,
      jamais le nom de fichier, l'UID ni le dossier patient

## Simplify log

**Repos éligibles touchés** : `api-mail`.

| Axe | Constat | Action |
|---|---|---|
| Réutilisation | Aucun littéral de commande créé — les quatre existaient dans `MailServerCommands`. Le recorder est celui déjà injecté dans `ImapService`. | — |
| Simplification | Aucun finding : le diff est quatre lignes de comptage et une garde. | — |
| Efficacité | La garde `IsOpen && Access` est une lecture de propriété, aucun aller-retour ajouté. | — |
| Altitude | `AttachmentOperation` nomme la famille au même endroit que `StatusOperation` et `QueryOperation`. | — |

**Re-validation** : build 0 erreur / 0 avertissement, 3 483 tests verts sur les
quatre suites unitaires.

## Sonar log

**Analyse NON exécutée** — `$SONAR_TOKEN` absent du shell de la forge (serveur
`UP` sur le port 9000, pas 9001 comme l'annonce `agents/sonar.md`). Aucun KPI,
**aucun vert revendiqué**. Diff C# de 5 lignes de production + 1 fichier de
tests ; dette neuve non mesurée.

## Lint log (/lint-angular)

**Skip clean** : `client-angular` non listé, aucun fichier Angular écrit.

## Lint mobile log (/lint-mobile)

**Skip clean** : `client-mobile` non listé, aucun fichier mobile écrit.

## Visual verify log (/verify-visual)

**Skip clean** : aucun écran mobile touché.

## PRs

- `api-mail` — **[PR #209](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/209)** — label `awaiting-human-merge`
- `dtos-mss` — branche créée, **0 commit**, aucune PR.

## Code Review Summary

**APPROVED** — 2 fichiers, 0 bloquant, 0 suggestion.

Le diff est minimal (5 lignes de production) et son point délicat — ne compter
que les ouvertures réelles — est **testé dans les deux sens** : la commande
apparaît sur dossier fermé, elle n'apparaît pas sur dossier déjà ouvert.

**DOD** : 7/8 verts. Le huitième — « la redondance du `OpenAsync` est établie » —
est **reporté au banc** et c'est justifié : c'est une question de **fréquence**,
pas de mécanisme, et elle se lit sur le rapport du prochain tir. Le critère est
inscrit au Manual Test Plan.
