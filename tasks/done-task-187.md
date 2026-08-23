# todo-task-187.md — Sessions IMAP détruites en cours d'usage : lots de messages perdus, verrous corrompus

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axes sessions IMAP et
> concurrence).

> ### Re-vérification du 2026-08-23 — **pertinente, mais une preuve sur six est corrigée**
>
> Chaque preuve rejouée sur `develop`. **La preuve 2 est corrigée par task-223 :
> elle doit sortir du périmètre.** Les autres tiennent, avec des références
> déplacées et deux atténuations partielles.
>
> | Preuve | 2026-07-25 | Au 2026-08-23 | État |
> |---|---|---|---|
> | 1. Expiration pendant l'usage | `MailClientSessionManager.cs:275`, `:515` | `GetOrCreateSession` **`:316-325`** (appelé par `LockImapClientAsync` **`:139`**) ; `CleanupExpiredSessions` **`:595`** | **valide** |
> | 2. Déverrouillage sur la mauvaise session | `:118` | **CORRIGÉE (task-223)** | **à retirer** |
> | 3. Destruction bloquante | `MailClientSession.cs:218-220` | `Dispose` **`:535-575`** — `_imapLock.Dispose()` **`:559`**, `DisconnectAsync(true).GetAwaiter().GetResult()` **`:570`** | **valide, atténuée** |
> | 4. Déconnexion pendant un flux | `BackgroundSyncManager.cs:206`, `:398` | `RemoveSession` **`:236`** ; `StopLocallyAsync(…, resetUserContext: true)` **`:249`** et **`:435`** ; `Reset()` **`:454`** | **valide** |
> | 5. Sémaphores partagés détruits | `:441` | `CleanupLocksForSession` **`:518`** | **valide, atténuée** |
> | 6. Registre d'arrière-plan | `BackgroundImapConnectionRegistry.cs:143-154` | `Dispose` **`:166-177`** — `entry.UsageLock.Dispose()` sans vérifier le prêt | **valide** |
>
> **Preuve 2 — corrigée, et il faut le dire précisément.** `LockImapClientAsync`
> capture le sémaphore **une seule fois** (`:141-144`, commentaire task-223) et
> rend un `ImapSessionLockHandle` ; `UnLockImapClient` (**`:236`**) libère **ce**
> handle, sans nouvelle recherche par clé. Le second jeton sur un sémaphore de
> capacité 1 n'est donc plus atteignable, et l'exception de libération d'un verrou
> libre non plus. Le même patron est appliqué au SMTP (`AcquireSmtpSlotAsync`
> `:181`, task-231). **Ne pas re-livrer ce correctif.**
>
> **Preuve 1 — toujours entière, et c'est elle qui porte la US.** `IsExpired`
> (`MailClientSession.cs:442-453`) reste **purement temporel** : aucune notion
> d'usage n'existe dans le modèle. Rien ne rafraîchit la voie IMAP pendant qu'elle
> travaille — contraste net et instructif : `AcquireSmtpSlotAsync` appelle
> `session.RefreshSmtp()` (**`:185`**) pour exactement cette raison, avec le
> commentaire qui l'explique. La voie IMAP n'a pas reçu son équivalent. Une session
> occupée depuis plus de 5 minutes est donc toujours détruite sous son détenteur —
> ce qui, depuis task-223, ne corrompt plus les verrous mais **casse toujours
> l'opération en vol** (`_imapLock` détruit, client déconnecté).
>
> **Atténuations à ne pas surestimer** :
> - Preuve 3 : `Dispose` est devenu **idempotent** (task-238, `:542`) et l'appel
>   bloquant est **gardé** par `IsConnected` (`:569`). Le gel de la boucle de
>   nettoyage par un serveur muet reste possible — `GetAwaiter().GetResult()` est
>   toujours là, sur le thread de nettoyage partagé.
> - Preuve 5 : task-058 a ajouté le garde `HasActiveSessionsForEmail` (`:545`) pour
>   les verrous partagés entre sessions du même praticien. Le cas d'origine subsiste :
>   un **travail d'arrière-plan** détenteur d'un verrou ne possède aucune session,
>   donc le garde ne le voit pas.

## Objective

Garantir qu'une session IMAP n'est jamais détruite pendant qu'elle est utilisée, et
qu'un verrou n'est jamais libéré au profit d'une autre session que la sienne.

Le nettoyage des sessions expirées ne tient aucun compte de l'usage en cours :
aucune session n'est marquée « occupée », et le temps d'accès n'est pas rafraîchi
pendant une opération longue. Une session peut donc être déconnectée et libérée
**au milieu d'une récupération de messages**. Les conséquences se cascadent :
lot de messages silencieusement perdu, libération d'un verrou appartenant à une
autre session (deux requêtes pilotant alors le **même** client IMAP, qui n'est pas
thread-safe), ou exception au retour du bloc de verrouillage.

**US backend-only (justification)** : cycle de vie des sessions côté serveur.

### Preuve (état actuel du code)

1. **Expiration pendant l'usage** —
   `src/Application/Session/MailClientSessionManager.cs:275` : le chemin de
   verrouillage crée la session par un `GetOrAdd` **sans** rafraîchir son temps
   d'accès (seuls `GetOrCreateImapClientAsync` et `RefreshSession` le font).
   `CleanupExpiredSessions` (`:515`) détruit toute session inactive depuis 5 minutes
   **sans vérifier si elle est verrouillée ou en cours d'usage** :
   `kvp.Value.Dispose()` puis `TryRemove`.
   Or `EnrichEmailsAsync` (`src/Application/Services/Implementation/ImapService.cs:713`)
   récupère, **sous un seul verrou**, les résumés puis les corps et archives de
   jusqu'à 50 messages : sur un serveur MSSanté lent, cela dépasse 5 minutes (le
   code journalise déjà des listages de dossiers de ~68 s).
   Le lot meurt alors dans le `catch (Exception)` de `:762`, journalisé « Error
   during IMAP fetch for enrichment », **sans reprise** : ces messages sont perdus
   jusqu'à une synchronisation ultérieure.
2. **Déverrouillage sur la mauvaise session** — au retour du bloc, `UnLockImapClient`
   (`:118`) retrouve la session **par clé** et libère le verrou de *ce qui occupe
   désormais la clé*. Si une requête concurrente a recréé une session et détient
   son verrou, la libération accorde un **second jeton** sur un sémaphore de
   capacité 1 : deux requêtes pilotent le même client IMAP — précisément l'erreur
   « ImapClient is currently busy processing a command in another thread » que les
   commentaires de `ImapFolderService.cs:84` et `EmailFlagService.cs:177` visent à
   prévenir. Si le verrou est libre, la libération lève une exception qui s'échappe
   du bloc en 500.
3. **Destruction bloquante et concurrente du client** —
   `src/Application/Session/MailClientSession.cs:218-220` : après une attente
   bornée à 2 s de la tâche de keep-alive, `Dispose` enchaîne
   **inconditionnellement** `_imapLock.Dispose()` puis
   `_imapClientWrapper.DisconnectAsync(true).GetAwaiter().GetResult()`. Si le
   keep-alive est encore en vol (connexion à demi-ouverte après coupure NAT), une
   seconde commande partit sur le même client. De plus l'appel bloquant s'exécute
   sur la boucle de nettoyage : **un** serveur qui ne répond pas gèle la reprise des
   sessions de **tous** les autres praticiens. (Viole aussi la règle S4462 du repo :
   pas de `.GetAwaiter().GetResult()` en flux normal.)
4. **Déconnexion pendant un flux** —
   `src/Application/Services/Implementation/BackgroundSyncManager.cs:206` et `:398` :
   à la déconnexion, `RemoveSession` détruit la session sans vérifier l'usage, puis
   `StopLocallyAsync(..., resetUserContext: true)` appelle immédiatement
   `runtime.UserContextInfo?.Reset()`. L'annulation étant coopérative, la
   synchronisation est encore en train de se dénouer : elle recopie alors un
   contexte vidé (`Email = ""`, chaîne de connexion vide) et la persistance des
   messages déjà récupérés échoue (« Host is null »). Les messages du lot sont
   perdus.
5. **Sémaphores partagés détruits sous leur détenteur** —
   `src/Application/Session/MailClientSessionManager.cs:441`
   (`CleanupLocksForSession`) : les sémaphores par email/dossier sont libérés dès
   qu'il n'y a plus de session **de premier plan**, alors que leur détenteur peut
   être un travail d'arrière-plan qui ne possède aucune session.
6. **Registre de connexions d'arrière-plan** —
   `src/Application/Session/BackgroundImapConnectionRegistry.cs:143-154` : `Dispose`
   détruit tous les sémaphores sans vérifier s'ils sont prêtés ; la libération
   ultérieure du prêt lève alors une exception depuis un chemin de destruction, à
   l'arrêt du service.

### Contenu attendu

1. **Notion d'usage explicite** : une session en cours d'utilisation ne doit
   **jamais** être recyclée. Compteur d'usage, marquage « occupée », ou rafraîchi
   du temps d'accès pendant l'opération — le mécanisme est un choix technique, la
   propriété est non négociable.
2. **Libération sûre** : la libération d'un verrou doit porter sur **l'instance**
   acquise, jamais sur ce qu'une recherche par clé retourne au moment du retour.
3. **Destruction ordonnée et non bloquante** : attendre effectivement la fin des
   opérations en vol avant de déconnecter et de libérer ; supprimer l'appel
   bloquant de la boucle de nettoyage (conformité S4462) de sorte qu'un serveur
   muet n'affecte qu'une session.
4. **Déconnexion propre** : ne pas réinitialiser le contexte utilisateur tant que
   les travaux qui le lisent ne sont pas terminés ; les messages déjà récupérés
   doivent être persistés ou explicitement re-planifiés, jamais perdus.
5. **Sémaphores partagés** : ne les libérer que sans détenteur ni attente, en
   tenant compte des travaux d'arrière-plan sans session.
6. **Pas de perte silencieuse** : un lot interrompu doit être re-planifié ou
   signalé — jamais avalé par un `catch` journalisé.

### Hors scope

- L'identité des mails (UIDVALIDITY) → task-179.
- Le plan de contrôle de la synchronisation (pause, état Redis) → task-188.
- La performance des requêtes de liste → task-191.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire : une session **en cours d'usage** n'est pas recyclée par le
      nettoyage, même au-delà du délai d'expiration (ce test doit échouer sur le
      code actuel — le vérifier explicitement)
- [x] ~~Test unitaire : la libération d'un verrou porte sur l'instance acquise~~
      — **livré par task-223** (`ImapSessionLockHandle`). Hors périmètre : ne pas
      re-livrer, ne pas re-tester (les tests de task-223 couvrent ce point)
- [ ] Test unitaire **de non-régression** : deux requêtes concurrentes ne peuvent
      jamais piloter le même client IMAP. Le mécanisme existe depuis task-223 ;
      ce qui reste à prouver ici, c'est qu'il **survit** au recyclage d'une
      session occupée (preuve 1) — c'est le scénario que task-223 ne couvre pas
- [ ] Test unitaire : destruction pendant un keep-alive en vol ⇒ pas de seconde
      commande concurrente, pas d'exception depuis le chemin de destruction
- [ ] Test unitaire : plus aucun `.GetAwaiter().GetResult()` sur le chemin de
      nettoyage (conformité S4462) ; un serveur muet n'affecte qu'une session
- [ ] Test unitaire : déconnexion pendant une synchronisation ⇒ le contexte n'est
      réinitialisé qu'après dénouement ; aucun « Host is null », aucun message
      récupéré perdu
- [ ] Test unitaire : un sémaphore partagé détenu par un travail d'arrière-plan
      n'est pas libéré par la disparition de la dernière session de premier plan
- [ ] Test unitaire : à l'arrêt du service, aucune exception depuis un chemin de
      destruction du registre de connexions
- [ ] Un lot d'enrichissement interrompu est re-planifié ou signalé — vérifié par
      test, plus de perte silencieuse
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. **Opération longue** : sur une boîte de test fournie (plusieurs centaines de
   messages, avec archives IHE_XDM pour alourdir), lancer l'enrichissement d'un
   gros dossier et laisser l'opération dépasser le délai d'expiration de session
   (5 min). Ralentir le serveur si besoin (le profil de latence dégradée du banc de
   charge task-173/174 est utilisable ici).
   **Attendu** : l'enrichissement se termine complètement ; aucun message manquant ;
   aucune ligne « Error during IMAP fetch for enrichment ». Avant correctif, le lot
   en cours est perdu en silence.
3. **Concurrence sur la même boîte** : depuis deux onglets du **même** praticien,
   naviguer simultanément dans les dossiers et lancer une synchronisation → aucune
   erreur « busy processing a command in another thread », aucun 500, aucune
   attente anormalement longue.
4. **Serveur muet** : couper brutalement le réseau vers le serveur IMAP pendant une
   session active (ou geler le conteneur mail), attendre le passage du nettoyage →
   les sessions des **autres** praticiens continuent d'être reprises normalement
   (avant correctif, la boucle de nettoyage se bloque).
5. **Déconnexion en cours de sync** : lancer une synchronisation complète puis se
   déconnecter immédiatement → pas de « Host is null » dans Seq ; les messages déjà
   récupérés sont soit persistés, soit re-planifiés à la synchronisation suivante.
6. **Arrêt du service** : arrêter l'application pendant une synchronisation
   d'arrière-plan → arrêt propre, sans exception de destruction dans les logs.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volet MSSanté
- **Exigences DSR honorées** : correctif de conformité — fiabilité et complétude de
  la réception MSSanté (un message reçu ne doit pas être perdu par un défaut de
  cycle de vie technique)
- **INS** : non applicable directement — mais les messages perdus peuvent porter
  des documents CDA avec INS, donc des documents cliniques jamais restitués
- **Authentification PS** : inchangée ; le correctif touche la réutilisation des
  sessions authentifiées, sans changer le moyen d'authentification
- **Habilitations** : inchangées. **Point de vigilance** : le défaut de libération
  croisée de verrou concerne des sessions du **même** praticien (clé
  `{email}_{clientSessionId}`) — il n'y a **pas** de franchissement de frontière
  entre praticiens ici (la fuite inter-praticiens est traitée par task-175)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : journaliser l'interruption et la re-planification d'un lot
  (évènement technique, sans contenu) — indispensable pour détecter une perte
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé — pas de nouveau traitement, pas de
  divulgation. Risque d'exactitude/disponibilité (art. 5.1.d) à mentionner au
  humain : des messages ont pu ne pas être restitués.

## Branches

- `api-mail` (pushed) : fix/task-187-sessions-imap-detruites-en-usage — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-187-sessions-imap-detruites-en-usage
- `dtos-mss` (pushed, auto-inclus) : fix/task-187-sessions-imap-detruites-en-usage — aucune modification attendue (cycle de vie des sessions IMAP, aucun contrat)
- `client-angular`, `client-blazor`, `client-mobile` : hors périmètre (`**Repos**: api-mail`, `**Single frontend**: true`)
- `devops`, `psc-proxy-*` : managed manually by the human

Préfixe `fix/` : correction de défauts de cycle de vie et de concurrence, pas
d'ajout de capacité.

**Pré-flight** : `api-mail`, `client-blazor`, `client-mobile`, `dtos-mss`, `sdk`,
`interop-cda` sur `develop`, arbres propres. `host` sans `.git` — pré-flight non
applicable (cf. avertissement CLAUDE.md).

## Develop log (2026-08-23)

Livré en `7bc5926` sur `api-mail`. `dtos-mss` : **aucun commit** — aucun contrat
touché, donc aucun publish NuGet, aucun bump consommateur.

### Ce que la re-vérification a changé dans le travail réel

La preuve 2 (déverrouillage sur la mauvaise session) est **livrée par task-223**
et n'a pas été re-livrée. Deux autres preuves avaient des **prémisses périmées**,
et le constater a changé le remède :

| Preuve | Prémisse de 2026-07-25 | État réel au 2026-08-23 |
|---|---|---|
| 1 | « `EnrichEmailsAsync` tient **un seul** verrou pour 50 messages » | Faux depuis task-228/239 : le verrou est pris et rendu **par message**. Le défaut subsiste, mais par un autre chemin — voir ci-dessous. |
| 1 (suite) | « le lot meurt dans le `catch`, **sans reprise** » | Faux depuis task-239/254 : les messages déjà lus sont persistés, le reste des UID reste `pending`. Un test d'intégration le prouve déjà (`EnrichmentPartialBatchFailureTests`). |

### ⭐ Le découpage par message a déplacé le défaut, il ne l'a pas fermé

C'est le point qui a orienté la conception. Avec des fenêtres de verrou **par
message**, un compteur d'usage ne suffit pas : entre deux messages d'un même lot,
**personne ne tient la session**. Un compteur seul l'aurait donc laissée ramassable
dans ces interstices — et le seul rafraîchi existant, `ConnectInternalAsync`, n'est
payé qu'**une fois par sous-lot** (15 messages par défaut).

D'où les **deux** mécanismes, et pas un :

1. un compteur d'usage, déclaré **avant l'attente** du verrou (une requête qui fait
   la queue en a besoin : la détruire lui laisserait un sémaphore que plus personne
   ne rend) ;
2. le **rendu du verrou redémarre l'horloge** IMAP, ce qui couvre les interstices.

### Une asymétrie IMAP/SMTP assumée

`ExitUse` ne rafraîchit **que** la voie IMAP. La voie SMTP est déjà rafraîchie à
l'emprunt, et son éviction propre (`EvictIdleSmtpConnection`, qui passe son tour si
le jeton est pris) protège déjà un envoi en cours. La rafraîchir au rendu aurait
déplacé la mesure d'inactivité SMTP « depuis la fin de l'envoi » — un changement de
sémantique hors sujet, et `SmtpConnectionEvictionTests` l'a signalé immédiatement.
Ce qui manquait à SMTP, c'était uniquement d'empêcher la destruction de la session
pendant l'envoi : le compteur d'usage s'en charge.

### La fermeture, et pourquoi l'ordre EST le correctif

`Dispose` disposait le sémaphore IMAP **puis** déconnectait, en bloquant. Trois
défauts en trois lignes. `DisposeAsync` : on annule le maintien, on l'attend, on
**prend** le verrou de chaque voie — l'obtenir *est* la preuve qu'aucune commande
n'est en vol, puisque le maintien tient ce même verrou pendant son NOOP — et
seulement alors on déconnecte. Chaque attente est bornée ; les fermetures d'un
balayage courent en parallèle.

`.GetAwaiter().GetResult()` a disparu (S4462). Le `Dispose` synchrone subsiste,
**sans IO ni attente**, pour les appelants qui ne peuvent pas attendre — c'est
exactement le raisonnement que `DiscardSmtpClient` documente déjà pour SMTP.

### Le test qui prouve la concurrence sans chronomètre

`AMutedServerDoesNotHoldUpTheCloseOfTheOtherSessions` n'utilise **pas** de
chronomètre : la session saine doit avoir parlé à son serveur **alors que** la
session muette attend encore. En série — le comportement d'avant — c'est
impossible. Un test qui mesure des millisecondes est un test qui clignote.

### Ce que le rouge initial a montré

Les 5 tests de `SessionInUseLifecycleTests` étaient **rouges** sur `develop` (4/5 en
assertion, le 5ᵉ vert par accident de séquencement). Le plus instructif est
`TheHeldSemaphoreStillSerialisesAfterASweepHasSeenTheSessionExpired` : après le
balayage, une **seconde** prise du verrou de session **était accordée**. La
conséquence n'était donc pas théorique — deux requêtes sur un `ImapClient` qui
n'est pas thread-safe, c'est-à-dire l'erreur « busy processing a command in another
thread » que deux commentaires du dépôt cherchent à prévenir.

### Deux tests de task-223 ont dû changer de mise en scène

Ils recyclaient l'entrée de session **via le balayage d'expiration** — ce que
task-187 rend désormais impossible. La propriété de task-223 reste nécessaire :
le recyclage par **déconnexion pendant une opération** est toujours atteignable
(`RemoveSession` détache sans attendre, un onglet resté ouvert recrée l'entrée).
Les tests passent donc par cette porte. Le troisième
(`ReleasingADisposedSessionLockIsLoggedAndSwallowed`) provoque désormais le
`Dispose` **synchrone** directement : les deux fermetures « en service » ne peuvent
plus disposer un sémaphore occupé, mais le rideau doit tenir sur ce chemin-là aussi.

### Tests

| Niveau | Nombre |
|---|---|
| Usage / balayage (`SessionInUseLifecycleTests`) | **5** |
| Fermeture ordonnée (`SessionCloseOrderingTests`) | **5** |
| Verrous partagés (`SharedLockReclaimTests`) | **5** |
| Dénouement avant reset (`SyncUnwindBeforeContextResetTests`) | **3** |
| Registre de fond (`BackgroundImapConnectionRegistryTests`) | **+2** |

### État des suites (build en arbre, sans `--artifacts-path`)

| Suite | Résultat |
|---|---|
| Build solution | **0 erreur, 0 avertissement** |
| `domain` | **136 / 136** |
| `application` | 2181 / 2183 — les 2 échecs (`EnrichmentOperationScopeTests`) sont **identiques sur `develop` non modifié**, contre-épreuve faite par `git stash` |
| `infrastructure` | **464 / 464** |
| `api` | **685 / 685** (deux passes) |
| `integration` | **416 / 433**, 16 ignorés (`UC-AI-*`/Ollama) et **1 flaky** — `develop` en produit **aussi exactement 1**, un test différent à chaque tir (contre-épreuve faite) |

⚠️ **Piège d'outillage à consigner** : `--artifacts-path` (utilisé pour bâtir sans
tuer l'AppHost) **fait échouer par construction** tous les tests qui remontent
l'arborescence depuis le répertoire de sortie pour lire un fichier du dépôt —
`EmbeddingOptionsConsistencyTests`, les scans d'architecture, et **91 tests
d'intégration** (`DovecotFixture` cherche `src/AppHost/dovecot/dovecot.conf`). Ce
ne sont **pas** des régressions : contre-épreuve faite sur `develop` non modifié.
Mon propre test de conformité S4462 est tombé dans le même piège ; il localise
maintenant la source par `[CallerFilePath]`, ce qui est immunisé.

### Conformité S103 / S4462

`awk 'length($0)>150'` sur les 11 fichiers touchés : **aucune ligne**. Plus aucun
`.GetAwaiter().GetResult()` ni `.Wait(TimeSpan` dans `MailClientSession` — vérifié
par un test qui lit la source **hors commentaires** (les remarques de la task citent
l'appel supprimé pour expliquer pourquoi il l'est).

### Ce qui reste à la main de l'humain

Le Manual Test Plan porte sur des conditions que seul un banc vivant produit :
opération dépassant 5 minutes sur un serveur ralenti, deux onglets du même
praticien, coupure réseau brutale, déconnexion en cours de synchronisation, arrêt
du service. Les tests couvrent les **mécanismes** ; l'attestation `--i-tested`
couvre leur rencontre avec un vrai serveur MSSanté.

## Simplify log (2026-08-23)

Passe qualité `/forge-simplify` sur `api-mail` — commit `c92204f`.
Repos éligibles touchés : `api-mail` seul (pas de `dtos-mss`/`interop-cda`,
porteurs de contrat, ni de frontend).

### Ce qui a été corrigé

| # | Constat | Correction |
|---|---|---|
| 1 | L'appariement `EnterUse`/`ExitUse` vivait dans **5 `catch` dispersés** sur les deux voies. Un `catch` ajouté plus tard sans y penser aurait rendu la session **immortelle** — le balayage ne l'aurait plus jamais reprise. C'est l'exact inverse du défaut corrigé par la task, par la même porte. | `try/finally` avec un drapeau « repris par le jeton » : tous les chemins de sortie sont couverts, y compris ceux que personne n'a prévus, et le contrat est dit **une** fois. |
| 2 | Les trois issues de l'attente SMTP répétaient le même appel de métrique, à un argument près sur quatre. | `RecordSmtpLockWait(waitedFrom, outcome)` — les trois autres arguments ne peuvent plus diverger. |
| 3 | `TryReclaimSharedLock` gardait « absent » et « tenu » séparément alors que le traitement est le même ; `ObserveDetachedClosures` allouait une liste pour la fermeture **unique** de `RemoveSession`. | Gardes fusionnées ; surcharge au singulier. |

**Le point 1 est le seul qui compte vraiment**, et il mérite d'être nommé pour
ce qu'il est : un correctif de robustesse déguisé en simplification. La forme
d'origine était *correcte* — les cinq `catch` étaient exhaustifs le jour de leur
écriture. Ce qu'elle ne portait pas, c'est l'invariant : « l'usage appartient à
cette méthode jusqu'à ce que le jeton le reprenne ». Le `finally` le porte, donc
un futur chemin de sortie ne peut plus l'oublier.

### Ce qui n'a PAS été touché

- `dtos-mss` / `interop-cda` — porteurs de contrat, hors charte de l'étape.
- Le comportement : aucun test n'a été réécrit, et ils sont restés verts. La
  passe est quality-only ; la chasse aux bugs est `/code-review`.
- L'asymétrie `ExitUse` IMAP/SMTP — **délibérée et documentée**, pas une
  irrégularité à lisser (voir le Develop log).

### Validation

| Suite | Résultat |
|---|---|
| Build solution | **0 erreur, 0 avertissement** |
| `domain` | **136 / 136** |
| `application` | **2183 / 2183** |
| `infrastructure` | **464 / 464** (trois tirs) |
| `api` | **685 / 685** |
| Tests de session (filtre `~Session`) | **191 / 191** |
| Intégration (lot interrompu + drain de file) | **5 / 5** |
| S103 (`awk length>150`) | aucune ligne |

⚠️ Deux tests ont été **rouges au premier tir puis verts aux suivants** —
`EnrichmentOperationScopeTests.Assemble_is_the_remainder…` et
`MailReadObjectCountTests.GetMailsByUidsCountsEachLotItMaterialisesAsync`. Tous
deux lisent des **compteurs de métriques statiques** partagés entre collections
xUnit parallèles, et aucun n'a de lien causal avec le diff (attente de verrou
SMTP). Le premier échoue aussi sur `develop` non modifié (contre-épreuve faite
par `git stash`). Flakiness d'instrumentation pré-existante, consignée, non
corrigée ici : ce serait un autre sujet que la charte de cette étape.

## Sonar log (2026-08-23)

Quatre scans complets sur `fix/task-187-sessions-imap-detruites-en-usage`
(`begin` → build Release → 5 suites avec couverture OpenCover → `end`,
`EXECUTION SUCCESS` à chaque fois). Projet `healthplatform-api-mail`.
Correctif livré en `b239b6c`.

### KPIs qualité (baseline → final)

| Métrique | Baseline (task-267, 2026-08-22) | Après `/develop`+`/forge-simplify` | **Final (task-187)** | Δ vs baseline |
|---|---|---|---|---|
| **Quality Gate (new code)** | ERROR | ERROR | **ERROR** | inchangé |
| **Bugs** | 2 | **5** ⚠️ | **2** | **0** |
| **Reliability rating** | 3,0 | **4,0** ⚠️ | **3,0** | **0** |
| Code smells | 70 | 71 | **69** | **−1** |
| Vulnérabilités | 0 | 0 | **0** | 0 |
| Security rating | 1,0 | 1,0 | **1,0** | 0 |
| Maintainability rating | 1,0 | 1,0 | **1,0** | 0 |
| Coverage (projet) | 78,3 % | 88,0 % | **88,0 %** | +9,7 pts |
| `new_coverage` | 78,6 % | — | **88,1 %** (seuil 80 → OK) | |
| `new_violations` | 70 | 70 | **69** (seuil 0 → ERROR) | −1 |
| `new_duplicated_lines_density` | 0,055 % | — | **0,054 %** (seuil 3 → OK) | |
| `new_security_hotspots_reviewed` | 0 % | 0 % | **0 %** (seuil 100 → ERROR) | inchangé |
| Duplication projet | 0,3 % | 0,3 % | **0,3 %** | 0 |
| `ncloc` | 47 477 | 48 354 | **48 363** | +886 |

### ⭐ Le scan a trouvé un vrai défaut, et il avait raison

**3 bugs CRITICAL `S2952`** — « Move this 'Dispose' call into this class' own
'Dispose' method » — tous les trois **imputables à task-187**, avec la note de
fiabilité qui passait de **3,0 à 4,0**. Ce n'était pas un faux positif : ma
fermeture asynchrone libérait les champs de la classe (`_keepAliveCts`,
`_imapLock`, `_smtpLock`) depuis une méthode que l'analyseur ne reconnaît pas
comme une méthode de disposition.

**Deux réactions étaient possibles, et la première était mauvaise** :
1. renommer/contourner pour faire taire la règle ;
2. adopter le patron canonique.

D'abord tenté (1) sous une forme déguisée — passer la signature à
`DisposeAsync()` sans paramètre pour qu'elle soit le membre d'`IAsyncDisposable`.
**Le scan suivant a montré que ça ne suffisait pas** : `S2952` ne reconnaît que
`Dispose`/`Dispose(bool)`, pas la variante asynchrone. Il a donc fallu faire (2) :
la libération des champs vit maintenant dans `Dispose(bool)`, **un seul endroit**,
et `DisposeAsync` ne fait que ce qu'elle seule peut faire — attendre, parler au
serveur, puis déléguer.

**Et le détour a rendu le code meilleur, pas seulement conforme** : « on ne
dispose jamais un sémaphore que quelqu'un tient » est devenue **une** règle
(`DisposeIfFree`), valable pour les deux voies **et** les deux chemins de
fermeture. Avant, le chemin synchrone disposait inconditionnellement et
l'asynchrone conditionnellement — deux comportements pour une seule intention.
C'est la même règle que celle appliquée aux verrous partagés du gestionnaire.

### Attribution ligne à ligne du reste

Les 69 violations de la *new-code period* ont été rapportées à leur fichier et à
leur ligne, puis croisées avec `git diff origin/develop...HEAD`.

| Fichier de la task | Findings dedans |
|---|---|
| `src/Application/Session/MailClientSessionManager.cs` | **0** |
| `src/Application/Session/MailSessionLane.cs` | **0** |
| `src/Application/Session/ImapSessionLockHandle.cs` | **0** |
| `src/Application/Session/SmtpSessionSlot.cs` | **0** |
| `src/Application/Session/BackgroundImapConnectionRegistry.cs` | **0** |
| `src/Application/Services/Implementation/BackgroundSyncManager.cs` | **0** |
| Les 4 fichiers de tests neufs | **0** |
| `src/Application/Session/MailClientSession.cs` | **2 — prouvées antérieures** |

**Total imputable à task-187 : 0 violation.**

Les deux findings de `MailClientSession.cs` méritent d'être nommés parce que c'est
le fichier le plus touché, donc le cas où « antérieur » se démontre au lieu de
s'affirmer :

- **`S125` ligne 243** (bloc de commentaire de task-231 sur les deux horloges) ;
- **`S3776` ligne 331** (`StartKeepAlive`, complexité cognitive 19 > 15).

Les deux sont **byte-identiques à `develop`** (`md5sum` sur chaque bloc, contre
`git show origin/develop:…`), et mon diff sur ce fichier **commence à la ligne
437**. Aucune des deux lignes n'y est.

### Deux findings corrigés en plus des bugs

- **`S125`** sur le bloc de commentaire que `SweepExpiredSessions` avait **hérité**
  de `CleanupExpiredSessions` : le texte était antérieur, mais la **ligne** était
  neuve (je l'avais déplacé). L'explication est remontée dans la doc XML de la
  méthode — ce que prescrit `conventions/csharp.md`, entrée `S125`.
- **`CA1068`** sur un helper de test : le `CancellationToken` passe en dernier.

### Les deux conditions du Quality Gate qui restent ERROR

| Condition | Valeur | Seuil | Lecture |
|---|---|---|---|
| `new_violations` | 69 | 0 | **`new_lines` = 122 744.** La *new-code period* est `PREVIOUS_VERSION` datée du **2026-04-17** : elle englobe des dizaines de tasks déjà mergées. 69 violations sur 122 744 lignes ne décrivent pas un diff de ~1 400 lignes. Piège déjà consigné pour cette EPIC. |
| `new_security_hotspots_reviewed` | 0 % | 100 % | 13 hotspots projet, **aucun** dans les fichiers de la task. Exige une revue humaine dans l'UI Sonar, que la forge ne peut pas faire à sa place. |

### Tests pendant le scan final (Release)

| Suite | Résultat |
|---|---|
| `domain` | **136 / 136** |
| `application` | **2183 / 2183** |
| `infrastructure` | **464 / 464** |
| `api` | **685 / 685** |
| `integration` | **417 / 433**, 16 ignorés (`UC-AI-*`/Ollama), **0 échec** |

Build Release **0 erreur**. `awk length>150` sur les fichiers touchés : aucune ligne.

⚠️ **Flakiness d'instrumentation, consignée** : `MailRepositoryEnrichPersistInstrumentationTests`,
`EnrichmentOperationScopeTests`, `MailReadObjectCountTests`, `MailExportServiceTests`
et un test d'intégration différent à chaque tir se sont montrés rouges **une fois**
puis verts. Tous lisent des compteurs de métriques statiques partagés entre
collections xUnit parallèles, ou sont des flakies déjà documentés (PDF/PdfPig,
annulation IMAP). Contre-épreuves faites sur `develop` non modifié. Le tir final
est vert sur les cinq suites.

## Lint log (2026-08-23)

⏭️ **Skip propre** — `client-angular` n'est pas touché par cette task
(`**Repos**: api-mail`, `**Single frontend**: true`). Aucun fichier de
`Client/Angular/front/` dans le diff, donc rien à linter. La chaîne enchaîne.

## Lint mobile log (2026-08-23)

⏭️ **Skip propre** — `client-mobile` n'est pas touché par cette task
(`**Repos**: api-mail`). Aucun fichier de `Client/Mobile/` dans le diff. La
chaîne enchaîne.

## Visual verify log (2026-08-23)

⏭️ **Skip propre** — aucun écran mobile touché. La task est backend-only
(`**Repos**: api-mail`), il n'y a ni `## Stitch design log` ni fichier de
`Client/Mobile/` dans le diff. Rien à capturer.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/200
  — label `awaiting-human-merge`, état MERGEABLE.
- `dtos-mss` : branche `fix/task-187-sessions-imap-detruites-en-usage` créée par
  `/start` (auto-inclusion), **aucun commit** — cycle de vie des sessions, aucun
  contrat touché. Pas de PR, pas de publish NuGet.
- `client-angular`, `client-mobile`, `client-blazor` : hors périmètre
  (`**Repos**: api-mail`, `**Single frontend**: true`).
- `devops`, `psc-proxy-*` : managed manually by the human.

## Code Review Summary

**Verdict : APPROVED** — 14 fichiers revus, **1 défaut bloquant trouvé et
corrigé pendant la revue**, 2 suggestions non bloquantes, 0 blocage résiduel.

### ⭐ Ce que la revue a trouvé, et qu'aucun test n'aurait vu

Commit `8623662`. Drainer une voie à la fermeture, c'est **prendre** son verrou
et ne plus le rendre : son compteur tombe à zéro parce que c'est **la fermeture**
qui le tient. La libération lisait « compteur à zéro ⇒ encore détenu » et
laissait donc vivre le sémaphore d'une voie **parfaitement libre**, sur le chemin
**nominal** — l'inverse exact du commentaire qui l'accompagnait.

Le point qui compte n'est pas l'impact (modeste : un `SemaphoreSlim` sans
`AvailableWaitHandle` demandé ne retient aucune ressource non gérée) mais le
fait qu'**un commentaire décrivait l'inverse du code**. Corrigé avant l'ouverture
de la PR, avec un test vérifié **rouge** sans le correctif (`git stash` de la
seule source). Aucun test existant ne l'aurait vu : rien n'assertait la
libération.

| Fichier | Verdict |
|---|---|
| `Session/MailClientSession.cs` | ✅ compteur d'usage `Interlocked`/`Volatile` ; fermeture ordonnée ; patron canonique `IDisposable`/`IAsyncDisposable` |
| `Session/MailClientSessionManager.cs` | ✅ usage déclaré avant l'attente, refermé par `try/finally` ; fermetures parallèles et bornées |
| `Session/ImapSessionLockHandle.cs` | ✅ le jeton porte la session ; fin d'usage dans un `finally` |
| `Session/SmtpSessionSlot.cs`, `MailSessionLane.cs` | ✅ asymétrie de rafraîchi documentée |
| `Session/BackgroundImapConnectionRegistry.cs` | ✅ un bail en cours garde son sémaphore |
| `Services/Implementation/BackgroundSyncManager.cs` | ✅ dénouement signalé dans le `finally`, attente bornée |
| 4 fichiers de tests neufs (21 cas) + 3 adaptés | ✅ faits mesurés ; le test de concurrence ne chronomètre pas |

### Suggestions (non bloquantes)

1. **Une session « occupée » n'est jamais reprise** — un jeton fui rend la
   session immortelle. La seconde moitié du problème (verrou pris à jamais)
   existait déjà ; la première est nouvelle. Une **métrique** « sessions
   maintenues par l'usage » rendrait la fuite visible. Task transverse
   d'observabilité.
2. **`Task.Delay(SyncUnwindTimeout)` sans jeton** — minuteur qui vit jusqu'à son
   terme même quand le dénouement arrive avant. Sans conséquence fonctionnelle.

### Sécurité / données de santé

Aucune donnée de santé dans les nouveaux journaux : identifiants techniques de
session, noms de voie, durées, booléens. Aucun INS, aucun nom de patient, aucun
contenu de message. L'adresse MSSanté du praticien apparaît dans `{Email}` /
`{Key}` — PII professionnelle, motif préexistant de ces fichiers, sujet de
task-184. Aucun secret, aucune surface HTTP touchée, aucun contrat modifié.

## DOD — vérification

| Critère | Verdict |
|---|---|
| Build 0 erreur | ✅ **0 erreur, 0 avertissement** |
| Tests 0 échec (hors flaky documentés) | ✅ domain 136/136, application **2184/2184**, infrastructure 464/464, api 685/685, intégration **417/433** (16 ignorés `UC-AI-*`/Ollama, 0 échec) |
| Session en usage non recyclée, **test rouge sur le code actuel vérifié** | ✅ `ASessionHeldByAnOperationSurvivesTheSweepEvenPastItsIdleTimeout` — rouge sur `develop`, constaté |
| ~~Libération sur l'instance acquise~~ | ⏭️ **task-223**, hors périmètre |
| Non-régression : deux requêtes ne pilotent jamais le même client IMAP | ✅ `TheHeldSemaphoreStillSerialisesAfterASweepHasSeenTheSessionExpired` — **rouge sur `develop`**, et c'est le test qui montre la conséquence |
| Destruction pendant un keep-alive en vol | ✅ `ClosingASessionNeverSendsASecondCommandWhileOneIsInFlight`, `TheSemaphoreOfABusyLaneSurvivesTheClose` |
| Plus de `.GetAwaiter().GetResult()` sur le chemin de nettoyage ; serveur muet isolé | ✅ `NoBlockingWaitRemainsOnTheSessionClosePath` (lit la source hors commentaires), `AMutedServerDoesNotHoldUpTheCloseOfTheOtherSessions` (prouve la **concurrence**, pas un chronomètre) |
| Déconnexion pendant sync ⇒ contexte réinitialisé après dénouement | ✅ `SyncUnwindBeforeContextResetTests` (3 cas, dont le témoin d'expiration) |
| Sémaphore partagé tenu par un travail d'arrière-plan | ✅ `SharedLockReclaimTests` (5 cas : fetch, enrich-persist, dossier, verrou libre, expiration) |
| Arrêt du service sans exception depuis le registre | ✅ `Dispose_LeavesTheSemaphoreOfALeasedEntryToItsHolder`, `Dispose_StillClosesTheClientOfALeasedEntry` |
| Lot d'enrichissement interrompu re-planifié ou signalé | ✅ **déjà livré par task-239/254** — `EnrichmentPartialBatchFailureTests` 2/2 vert, non re-livré |
| Aucune donnée de santé en clair dans les logs | ✅ vérifié sur les 13 nouveaux messages de journal |

## Étapes de la chaîne

| Étape | Résultat |
|---|---|
| `/develop` | ✅ `7bc5926` — 20 tests, dont 5 rouges sur `develop` avant correctif |
| `/forge-simplify` | ✅ `c92204f` — l'appariement d'usage passe de 5 `catch` à un `finally` |
| `/sonar` | ✅ `b239b6c` — 4 scans ; 3 bugs CRITICAL **imputables** trouvés et corrigés (patron canonique) ; **0 finding imputable au final** |
| `/lint-angular` | ⏭️ skip — `client-angular` non touché |
| `/lint-mobile` | ⏭️ skip — `client-mobile` non touché |
| `/verify-visual` | ⏭️ skip — aucun écran mobile touché |
| `/review` | ✅ APPROVED après correction du défaut trouvé (`8623662`), PR #200 ouverte |
