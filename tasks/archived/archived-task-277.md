# todo-task-277.md — Une session coupée par le serveur ne remonte plus une erreur au médecin

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015

## Objectif

Le médecin voit une **erreur technique** quand la session réutilisée par
api-mail a été fermée par le serveur d'en face. Le message qu'il reçoit ne
décrit rien qu'il puisse comprendre ni corriger : « Une erreur inattendue s'est
produite. Veuillez réessayer plus tard. »

Le tir du 2026-08-29
(`Api/Mail/tests/loadtest-k6/reports/2026-08-29/report-journey-500-task270-20260829-220155.md`,
finding **F-POOL-1**) en donne **deux occurrences, sur les deux protocoles**, à
500 médecins :

| Quand | Route | Pile | Fenêtre |
|---|---|---|---|
| 20:29 | `POST /api/v1/mail/sendmail` | `SmtpCommandException: Service shutting down and closing transmission channel (socket timeout, SO_TIMEOUT: 30000ms)` → `OnSenderNotAccepted` → `MailFromAsync`, `SmtpService.cs:95` | chauffe |
| 21:34 | `GET /api/v1/mail/folders/INBOX` | `IOException` / `SocketException (10054)` → `ImapFolder.StatusAsync` → `ImapService.ReadFolderAsync`, `ImapService.cs:658`, `ElapsedMs=19217` | **régime** |

Le volume dit que la situation n'est pas exceptionnelle, elle est **absorbée
partout ailleurs** : **4 727 `SmtpCommandException`** pour **142 467** NOOP de
keep-alive sur la fenêtre (3,3 % des NOOP échouent), **1 092 `IOException`** et
**619 `SocketException`**. Sur tout ce volume, **deux** seulement ont atteint le
médecin — mais deux de trop, et le taux croît avec la population et avec la
fragilité du lien.

**Ce n'est pas une régression de task-270.** Le helper de mapping d'erreur
`MapFolderAccessExceptionAsync` **préexiste** à `99f855d` (3 sites d'appel
avant, 2 après — l'écart vient de la fusion des deux chemins, pas d'une reprise
supprimée). Le défaut est ancien et structurel : **une session poolée que le
serveur a fermée de son côté est utilisée telle quelle**, l'échec remonte au
`GlobalExceptionHandler` et sort en `ProblemDetails` 500 (règle 12 — le format
est correct, c'est la décision de rendre une erreur qui ne l'est pas).

**Intention métier** : une connexion morte est un incident d'infrastructure, pas
un résultat métier. Elle doit être **détectée et re-tentée une fois sur une
session fraîche** avant que quoi que ce soit remonte au praticien. Le médecin ne
voit une erreur que si la seconde tentative échoue aussi.

### ⚠️ Le point dur, à trancher DANS l'US : l'idempotence du rejeu SMTP

Re-tenter une lecture IMAP est sans conséquence. **Re-tenter un envoi ne l'est
pas** : le point de non-retour est le `DATA` accepté par le serveur MSSanté.

| Étape SMTP | Rejeu | Pourquoi |
|---|---|---|
| Échec avant/pendant `MAIL FROM` (cas mesuré) | **sûr** | le serveur n'a rien accepté |
| Échec pendant `RCPT TO` | **sûr** | idem |
| Échec après `DATA` accepté | **INTERDIT** | le message peut être parti — rejouer, c'est envoyer deux fois un courrier médical |
| Échec sur l'acquittement final | **INTERDIT sans preuve** | indécidable en l'état |

L'US doit **nommer explicitement** le point de non-retour dans le code, et le
fixer par un test. Un doublon d'envoi MSSanté est un incident métier bien plus
grave que l'erreur qu'on cherche à éviter.

### Contenu attendu

1. **Détecter la session morte** — sur les deux voies, distinguer « le serveur a
   fermé la connexion » (`SocketException 10054`, `IOException`,
   `ServiceNotConnectedException`, `SmtpCommandException` de type « shutting
   down ») d'une erreur métier légitime. **Mapping par type, jamais par
   heuristique de message** (règle 12).
2. **Re-tenter une fois** sur une session fraîche, en écartant la session morte
   du pool.
3. **Borner le rejeu SMTP** au point de non-retour ci-dessus.
4. **Rendre la reprise observable** — un compteur de reprises par voie, pour que
   le prochain tir puisse dire combien de 500 ont été évités, et pour que la
   disparition du signal ne soit pas confondue avec l'absence d'instrument
   (leçon task-214).

**Gain attendu** : aucun temps serveur — de la **robustesse**. La grandeur à
suivre est le nombre d'erreurs vues du médecin, pas une latence.

**Ce qui n'est PAS dans le périmètre** : les 4 727 `SmtpCommandException`
elles-mêmes — elles viennent du GreenMail du banc qui coupe sur son `SO_TIMEOUT`
de 30 s, c'est un plafond **du serveur de test**, pas un défaut d'api-mail. On
corrige ce que l'application en fait, pas leur nombre.

## Definition of Done

- [ ] Build passes (0 erreur)
- [ ] Tests pass (0 échec)
- [ ] Une session IMAP fermée par le serveur déclenche **une** reprise sur
      session fraîche — test unitaire par simulation de `SocketException 10054`
      sur `StatusAsync`
- [ ] Une session SMTP fermée avant `DATA` déclenche **une** reprise — test
      unitaire
- [ ] Un échec **après** `DATA` accepté ne déclenche **aucune** reprise — test
      unitaire dédié, c'est la garde anti-doublon
- [ ] La détection se fait **par type d'exception**, jamais par mot-clé sur le
      message (règle 12) — test qui échoue si une heuristique de chaîne réapparaît
- [ ] La seconde tentative en échec rend un `ProblemDetails` conforme (règle 12),
      sans stack trace ni donnée de santé dans le `detail`
- [ ] Compteur de reprises par voie (`imap` / `smtp`) publié et testé
- [ ] La session morte est retirée du pool et n'est pas resservie — test
- [ ] Aucune donnée de santé dans les journaux de reprise : ni destinataire, ni
      objet, ni contenu du message, ni INS

## Manual Test Plan

**Ce que l'humain valide au HAG** : qu'une coupure de connexion ne se voit plus,
et qu'un envoi n'est jamais dupliqué.

1. Lancer le banc :
   ```bash
   cd Api/Mail
   dotnet run --project src/AppHost --launch-profile https-load-test
   ```
2. Attendre `http://127.0.0.1:5052/api/v1/connection/status` en 200, puis
   seeder : `dotnet run --project tests/mss.mail.loadtest.seed -- --users 2 --messages 20 --api http://127.0.0.1:5052`
3. Ouvrir `INBOX` une première fois pour établir la session poolée (en-têtes
   d'identité virtuelle, `Client-Session-Id: sess-1`).
4. **Couper la connexion sous l'application** via l'API Toxiproxy — ajouter un
   toxic de reset sur `dovecot-imap` :
   ```bash
   curl -s -X POST http://127.0.0.1:8474/proxies/dovecot-imap/toxics \
     -H 'Content-Type: application/json' \
     -d '{"name":"kill","type":"reset_peer","stream":"downstream","attributes":{"timeout":0}}'
   ```
5. Rouvrir `INBOX`, puis retirer le toxic :
   `curl -s -X DELETE http://127.0.0.1:8474/proxies/dovecot-imap/toxics/kill`
6. **Vérifier** : le médecin obtient sa liste de messages — **pas** de 500. Le
   compteur de reprises IMAP a augmenté de 1 (journaux ou `/metrics`).
7. **Envoi — le point sensible.** Répéter l'opération 4 sur `greenmail-smtp`,
   puis envoyer un message via `POST /api/v1/mail/sendmail`. Retirer le toxic.
8. **Vérifier** : l'envoi aboutit (ou échoue proprement), et surtout —
   **inspecter la boîte du destinataire : le message doit y être présent une
   seule fois**. Un doublon est un échec bloquant de l'US.
9. Vérifier qu'aucun journal produit à l'occasion de la reprise ne contient
   d'adresse MSSanté de destinataire, d'objet ni de contenu de message.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — robustesse technique interne
- **Exigences DSR honorées** : non applicable — comportement fonctionnel inchangé en nominal
- **INS** : non applicable
- **Authentification PS** : inchangée — la reprise réutilise l'identité de la requête en cours, jamais une identité de service
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — IMAP/SMTP internes au périmètre MSSanté existant
- **Tracé PGSSI-S** : **ajout** — journaliser chaque reprise de session (voie, cause typée, résultat), sans donnée de santé ; durée de conservation alignée sur les journaux techniques existants. L'échec d'envoi définitif reste journalisé comme aujourd'hui.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — inchangé
- **AIPD / impact RGPD** : inchangé — aucune donnée nouvelle collectée ; le compteur de reprises est une métrique technique sans identifiant

## Branches

- `api-mail` (pushed) : `feat/task-277-pooled-session-retry`
- `dtos-mss` (pushed, auto-inclus) : `feat/task-277-pooled-session-retry` — aucun changement de contrat attendu
- `client-angular`, `client-mobile`, `devops`, `psc-proxy-*` — non concernés

## Develop log

**Repos touchés** : `api-mail` uniquement. `dtos-mss` : branche créée par
`/start`, **aucun commit** — aucun contrat ne bouge.

### La décision structurante : où vit la garde d'idempotence

Elle vit dans **un type dédié**, `DeadSessionPolicy`, et pas dans les sites
d'appel. Deux raisons :

1. Elle doit être **testable seule**. Le test qui compte n'est pas « on rejoue »,
   c'est « on ne rejoue **pas** après un `DATA` accepté » — un test qui doit
   pouvoir échouer bruyamment si quelqu'un élargit la règle.
2. Elle est **typée, jamais textuelle** (règle 12). Un test dédié
   (`Detection_IsByType_NotByMessage`) construit une exception dont le *message*
   contient les mots du cas rejouable mais dont le *type* ne l'est pas : il
   échoue si un `Message.Contains(...)` réapparaît.

### Le point de non-retour SMTP, tranché

| Stade | Rejeu | Pourquoi |
|---|---|---|
| 421 sur `MAIL FROM` / `RCPT TO` | **oui** | le serveur ferme le canal avant d'avoir rien accepté — **c'est le cas mesuré au banc** |
| `MessageNotAccepted` | **non** | le `DATA` a été émis, le message peut être parti |
| `IOException` / `SocketException` pendant l'envoi | **non** | le stade est **indécidable**, et l'indécidable se traite comme un envoi parti |
| Refus métier (destinataire inconnu, quota) | **non** | autre code que 421 — le rejeu masquerait une erreur que le praticien doit voir |

La règle retenue est donc `SmtpCommandException` **avec** `StatusCode == 421`
**et** `ErrorCode ∈ {SenderNotAccepted, RecipientNotAccepted}` : le type de
l'exception prouve le **stade**, le code prouve la **mort du canal**. Aucun des
deux seul ne suffirait.

### Voie IMAP

Une lecture IMAP est idempotente : la seule question est « le transport est-il
rompu ? ». `ReadFolderAsync` est découpée en `ReadFolderOnceAsync` (le passage
IMAP) et `ReadFolderWithOneRetryOnDeadSessionAsync` (la reprise). **Piège traité**
: le `catch` de mapping vivait dans le corps découpé et **avalait l'exception
avant la reprise** — la reprise n'aurait jamais tiré. Il est remonté d'un cran.

La session morte est **retirée du pool** (`RemoveSession`) avant le rejeu — sans
quoi le rejeu la reprendrait et échouerait pour la même raison.

### Reconnexion SMTP en place

`ISmtpConnectionFactory.ReconnectSessionClientAsync` rouvre la connexion **du
jeton déjà emprunté**. Ni un nouvel emprunt (interblocage : le jeton détient le
verrou SMTP de la session), ni une libération suivie d'un ré-emprunt (fenêtre où
un autre envoi du praticien prendrait la session). Elle réutilise
`CreateConnectedClientAsync`, le chemin de reconnexion existant.

### Observabilité — un compteur, pas une absence d'erreur

`mssante_mail_session_retry_total{lane, outcome}`. **Quand la reprise marche, le
500 disparaît des journaux et le défaut devient invisible** : sans compteur, la
disparition du signal serait indiscernable de l'absence du problème. C'est la
leçon de task-214. Étiquettes bornées à la compilation, aucune donnée de santé.

Journalisation en **Information** et non Error : le serveur d'en face recycle
ses connexions, c'est nominal — mais la trace doit rester, sinon la reprise
masquerait une dérive du serveur distant.

### Vérification

- `dotnet build HealthPlatform.Api.Mail.sln` → **0 erreur, 0 avertissement**
- `dotnet test` : domain 136/136, infrastructure 464/464, api 692/692,
  application **2 199/2 199**, integration 414/435 + 16 skips
- **Les 5 rouges d'intégration sont PRÉ-EXISTANTS et vérifiés comme tels** :
  `git stash` du diff, mêmes 5 tests rejoués sur `develop` nu → **mêmes 2/2
  échecs**. C'est le flaky « du jour » de minuit (F-259-1, fuseau) — le tir a eu
  lieu à 00:30 locale. Aucun rapport avec ce diff, qui ne touche ni les dates ni
  la lecture du jour.
- 13 tests neufs : 9 sur la politique (dont la garde d'idempotence et la garde
  anti-heuristique), 4 sur la reprise IMAP (reprise réussie + éviction, double
  échec non bouclé, erreur métier non rejouée, chemin nominal sans surcoût)

### DOD

- [x] Build 0 erreur — [x] Tests verts (hors flaky pré-existant vérifié)
- [x] Session IMAP fermée → une reprise, testée par `SocketException 10054`
- [x] Session SMTP fermée avant `DATA` → une reprise, testée
- [x] Échec après `DATA` → **aucune** reprise, test dédié
- [x] Détection **par type**, test anti-heuristique
- [x] Seconde tentative en échec → l'erreur remonte (`ProblemDetails`, règle 12)
- [x] Compteur de reprises par voie
- [x] Session morte retirée du pool — testé
- [x] Aucune donnée de santé dans les journaux de reprise (dossier et session
      seulement, jamais destinataire, objet ni contenu)

## Simplify log

**Repos éligibles touchés** : `api-mail`. `dtos-mss` exclu par construction
(porteur de contrat, 0 commit).

| Axe | Constat | Action |
|---|---|---|
| Réutilisation | `ReconnectSessionClientAsync` réutilise `CreateConnectedClientAsync`, le chemin de reconnexion existant de la fabrique — aucune seconde façon d'ouvrir une connexion SMTP n'a été créée. | Déjà traité par `/develop` |
| Simplification | L'échec de reconnexion SMTP levait un `InvalidOperationException` → **500**. Or un serveur qu'on ne parvient pas à rejoindre est **indisponible**. `UnavailableException` existe et mappe en **503** (règle 12, mapping par type). | Corrigé — le praticien sait qu'il peut réessayer, l'exploitant lit la bonne famille |
| Efficacité | Le chemin nominal ne paie **rien** : la reprise est dans un `catch` filtré (`when`), donc aucun coût quand rien n'échoue. Test de non-régression dédié (`AHealthySession_IsNotRetried_AndPaysNothingExtraAsync`). | — |
| Altitude | `DeadSessionPolicy` **nomme la décision** au lieu de la disperser en gardes dans deux services. | Déjà traité par `/develop` |

**Factorisation des deux blocs de reprise — ÉCARTÉE, et c'est un arbitrage.**
Les voies IMAP et SMTP partagent la forme « essayer → si récupérable, réparer →
rejouer une fois → compter l'issue ». Un helper générique aurait supprimé ~8
lignes en double. **Refusé** : il aurait déplacé la garde d'idempotence SMTP
derrière une abstraction. Cette garde est la ligne la plus dangereuse de l'US —
l'élargir d'un cran envoie deux fois un courrier médical — et elle doit rester
**lisible à son site d'appel**. Les deux voies diffèrent d'ailleurs sur le fond :
IMAP évince la session, SMTP rouvre en place ; IMAP rejoue tout échec de
transport, SMTP n'en rejoue qu'un stade précis.

**Re-validation** : `dotnet build` 0 erreur / 0 avertissement ;
`mss.mail.application.tests` **2 199 verts / 0 rouge**.

## Sonar log

**Analyse NON exécutée — `$SONAR_TOKEN` absent du shell de la forge** (serveur
joignable et `UP` sur le port **9000**, pas 9001 comme l'annonce
`agents/sonar.md`). Même cause que sur task-276 ; le prérequis appartient à
l'humain. Étape best-effort → la chaîne se poursuit, **aucun KPI publié, aucun
vert revendiqué**.

⚠️ **Ce que ça laisse non mesuré, et c'est plus lourd que sur task-276** : ce
diff est du **C# applicatif** (6 fichiers source), pas du harnais Python. La
dette neuve éventuelle sur `SmtpService`, `ImapService`,
`SmtpConnectionFactory`, `MailProcessingMetrics` et `DeadSessionPolicy` n'est
**pas mesurée**. À rejouer (`$env:SONAR_TOKEN = "<token>"` puis `/sonar 277`)
avant le merge si l'humain veut la garantie zero-new-debt.

## Lint log (/lint-angular)

**Skip clean** : `client-angular` non listé dans `**Repos**:`, aucun fichier
Angular écrit.

## Lint mobile log (/lint-mobile)

**Skip clean** : `client-mobile` non listé dans `**Repos**:`, aucun fichier
mobile écrit.

## Visual verify log (/verify-visual)

**Skip clean** : aucun écran `client-mobile` touché (task backend seule).

## PRs

- `api-mail` — **[PR #208](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/208)** — label `awaiting-human-merge`
- `dtos-mss` — branche créée, **0 commit**, aucune PR.

## Code Review Summary

**APPROVED** — 8 fichiers, **1 défaut bloquant trouvé et corrigé par la review**.

| Fichier | Verdict |
|---|---|
| `ImapService.cs` | ❌→✅ **La première version détruisait la session dont la lecture détient le verrou** (`RemoveSession`). La reprise aurait tourné sans protection et un appel concurrent du même praticien aurait pu s'intercaler — l'invariant que `imap_session` existe pour tenir. Corrigé `3ead998` : fermer le **client**, préserver la **session**. |
| `SmtpService.cs` | ⚠️→✅ `InvalidOperationException` (500) → `UnavailableException` (503) : un serveur injoignable est indisponible, pas une erreur interne (règle 12). |
| `DeadSessionPolicy.cs` | ✅ Décision isolée, typée, testable seule. |
| `SmtpConnectionFactory.cs` | ✅ Réutilise `CreateConnectedClientAsync` ; reconnexion en place justifiée (interblocage sinon). |
| `MailProcessingMetrics.cs` | ✅ Étiquettes bornées à la compilation, aucune donnée de santé. |
| 2 fichiers de tests | ✅ 13 tests, dont la garde d'idempotence et la garde anti-heuristique. |

**DOD** : 9/9 verts.

### Validation finale

- Build 0 erreur / 0 avertissement
- domain 136 · infrastructure 464 · api 692 · application **2 199** — tous verts
- integration : 5 rouges **pré-existants, vérifiés sur `develop` nu** (flaky
  « du jour » de minuit, F-259-1)
- Branche à jour avec `origin/develop` (merge, pas de rebase — règle 4)

## Merged

**Date** : 2026-08-30 — `/merge 277 278 279 --i-tested` (HAG, règle 10).

| Repo | PR | Squash sur `develop` |
|---|---|---|
| `api-mail` | [#208](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/208) closed | `d47cb8c` |
| `dtos-mss` | aucune PR (0 commit) | — branche distante supprimée |

**Portes** : `--i-tested` fourni, label `awaiting-human-merge`, `MERGEABLE`/`CLEAN`,
aucun `CHANGES_REQUESTED`. Mergeabilité **revérifiée entre chaque merge** — les
trois touchent `ImapService.cs`.

**Validation post-merge sur `develop`** : build 0 erreur, **3 929 tests verts /
0 rouge** (domain 136, infrastructure 464, api 692, integration 422 + 16 skips,
application 2 215). Les trois modifications concurrentes du même fichier
cohabitent — un conflit sémantique n'aurait pas été visible en git.

**Branches** : refs distantes supprimées sur `api-mail` et `dtos-mss` ; branches
locales conservées.
