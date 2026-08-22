# todo-task-266.md — Le serveur calcule les fils de discussion pour tout le monde, alors que deux clients sur trois les jettent

**Repos**: api-mail, client-angular, client-mobile
**Epic**: E011
**Single frontend**: false
**Dependencies**: **task-194** (`todo`) borne le **coût** du calcul. Celle-ci
supprime le calcul **quand personne ne le demande**. Les deux sont
indépendantes et composables — ni l'une ni l'autre n'attend la seconde. Si
task-194 est livrée d'abord, le gain de celle-ci reste entier : ne pas faire
un travail borné coûte toujours moins que le faire.
**task-267** (`todo`, corpus de banc porteur de fils) **améliorerait** la mesure
sans la conditionner — voir « Ce que la mesure peut et ne peut pas montrer ».
**Priorité**: **3** — aucun défaut fonctionnel, aucun risque patient. C'est du
travail serveur gaspillé, sur le geste le plus fréquent de la messagerie.

> **Origine** : constat fait le 2026-08-20 en instruisant task-194, sur question
> humaine (« la détection des conversations est-elle conditionnée par les
> settings de l'utilisateur côté backend ? »). Rattaché à **E011 (performance
> api-mail)** : le comportement affiché ne change pour personne.

## Objective

Que le serveur ne calcule les compteurs de fils de discussion **que lorsqu'un
client les affiche réellement**.

## Ce qui est établi — état du code au 2026-08-20

### Le réglage existe, et le backend ne le lit jamais

`UserSettingsDto` porte `MailViewMode` (`List` | `Conversation`, **défaut
`List`**), persisté par utilisateur dans `UserSetting.SettingsJson`. Une
recherche de `MailViewMode` sur `Api/Mail/src/**/*.cs` renvoie **zéro
occurrence** : le backend le stocke et le restitue, sans jamais le consulter.
(Les nombreux « Conversation » du backend appartiennent tous au **chat IA** —
`AiConversationService`, `AiChatController` — sans rapport avec le fil des
mails.)

### L'enrichissement s'exécute inconditionnellement

`OnlineMailDataProvider.GetEmailHeadersAsync` appelle
`EnrichWithThreadCountsAsync(result)` sans aucune garde (`:87`) ; la seule
condition est `if (mails.Count == 0) return;` (`:94`). Suivent **deux**
allers-retours base par page — `GetThreadCountsAsync` puis
`GetLatestMessageIdsPerThreadAsync` — dont le premier
(`MailRepository.cs:4039`) matérialise **tous** les `MessageId` de la base puis
**toutes** les lignes porteuses de `References`/`InReplyTo`, filtrées seulement
sur `FolderPath != "Sent"`.

### Deux clients sur trois jettent le résultat — vérifié sur pièce

| Client | Gate | Comportement en mode `List` |
|---|---|---|
| `client-angular` | `threadCountFor()` (`mail-list.component.ts:752-757`) et `displayedMails` (`mail-state.service.ts:262-268`) | `threadCount` → `undefined`, aucun filtrage sur `isThreadRoot`. **Les deux champs sont ignorés.** |
| `client-mobile` | `threadCountFor()` (`mail-list.component.ts:92-93`) | `isConversation ? mail.threadCount : undefined`. **Ignoré de même.** |
| `client-blazor` | **aucun** | `MailListComponent.razor` consomme `mail.ThreadCount` **toujours** (`CalculateThreadCounts`, `GetThreadCount`). Zéro occurrence de `MailViewMode` dans tout `Client/Blazor`. |

Autrement dit : pour un praticien Angular ou Mobile resté sur le **défaut**
`List`, **100 %** de ce travail serveur est jeté par le client.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer qu'on peut brancher le calcul sur `MailViewMode` côté
  serveur.** C'était l'hypothèse de départ, et elle est fausse en l'état :
  `client-blazor` n'a **aucune** notion de mode de vue et affiche ses badges de
  fil en permanence. Un court-circuit piloté par le réglage lui ferait perdre
  ses badges pour tout utilisateur en mode `List` — c'est-à-dire, par défaut,
  **tous**. Ce serait une régression fonctionnelle déguisée en optimisation.
- **Ne pas présumer que le mécanisme peut être implicite.** Une préférence
  d'**affichage** d'un client ne doit pas piloter un **calcul** serveur partagé
  par trois clients : le jour où un quatrième arrive, il hérite d'un
  comportement qu'il n'a pas demandé et qu'il ne peut pas voir.
- **Ne pas présumer que le défaut peut être « ne pas calculer ».** Tout appelant
  existant qui ne dit rien doit continuer à recevoir exactement ce qu'il reçoit
  aujourd'hui. Le défaut est **compatible**, l'économie est **opt-in**.
- **Ne pas présumer que c'est un doublon de task-194.** task-194 rend le calcul
  **moins cher** ; celle-ci le rend **absent** quand il est inutile. Aucune ne
  dispense de l'autre : un calcul borné reste un calcul, et un client qui jette
  le résultat le jette aussi vite qu'il soit optimisé.
- **Ne pas présumer que le gain se déduit.** Il se mesure, sur le banc des
  tasks 173/174, avant/après, à protocole identique.

## Décisions prises (arbitrage humain du 2026-08-20)

1. **Mécanisme = paramètre de requête explicite**, pas lecture du réglage
   serveur. Le client déclare son besoin page par page. Défaut **compatible**
   (comportement actuel) pour tout appelant muet.
2. **Périmètre = `api-mail` + `client-angular` + `client-mobile`.**
   `client-blazor` est **hors périmètre et strictement inchangé** : il ne passe
   pas le paramètre, donc il continue de recevoir les compteurs. Lui câbler un
   mode de vue est une **fonctionnalité d'affichage** à part entière, pas un
   branchement — ce sera sa propre US si le besoin est confirmé.

Les deux clients gatés doivent **réellement** envoyer le paramètre : sans cela
le mécanisme existerait sans que personne ne l'emprunte, et le gain resterait
théorique. C'est la raison d'être du périmètre à trois repos.

## Ce que la US doit livrer

1. **Un paramètre de requête** sur les endpoints de listage qui traversent
   `GetEmailHeadersAsync`, permettant à l'appelant de déclarer qu'il n'a pas
   besoin des compteurs de fils. Nom et forme laissés à l'implémentation ;
   **contrainte ferme** : absent ⇒ comportement d'aujourd'hui, à l'identique.
2. **Le court-circuit** : quand l'appelant déclare ne pas en avoir besoin,
   **aucune** des deux requêtes de fil n'est émise. Pas « une requête plus
   petite » — **zéro requête**.
3. **Angular envoie le paramètre** depuis son `mailViewMode()` déjà existant.
4. **Mobile envoie le paramètre** depuis son `isConversation` déjà existant.
5. **Le harnais k6 doit pouvoir envoyer le paramètre.** Vérifié le 2026-08-20 :
   `getEmails` (`tests/loadtest-k6/lib/api.js`) construit
   `GET /mail/folders/{f}/emails/{uid1,uid2,…}` **sans aucune chaîne de
   requête**, et c'est ce que l'étape `read_list` de `journey.js:693` et le
   scénario `read` de `mixed.js:223` appellent. Sans modification du harnais,
   l'appel resterait muet, le défaut compatible s'appliquerait, et **la mesure
   « après » serait identique à la mesure « avant »** — le DOD de cette US
   serait invérifiable. Le harnais doit donc exposer les **deux jambes**.
6. **Mesure avant/après** sur le banc des tasks 173/174, à protocole identique,
   en mode `List` **et** en mode `Conversation` — le second doit être **inchangé**.
7. **Aucun changement d'affichage nulle part.** En mode `Conversation`, les
   compteurs et le repliement sont identiques. En mode `List`, l'écran est déjà
   identique aujourd'hui puisque les champs y sont ignorés — c'est précisément
   ce qui rend cette US sûre, et il faut le **prouver**, pas l'affirmer.

### Ce que la mesure peut et ne peut pas montrer

**Le corpus du banc ne contient aucun fil de discussion.** `BuildMime`
(`tests/mss.mail.loadtest.seed/Program.cs:312-334`) ne pose ni `In-Reply-To` ni
`References`. Sur `GetThreadCountsAsync`, cela signifie que la première requête
(scan complet des `MessageId`) est bien exercée, mais que la seconde ramène
**0 ligne** et que la boucle de comptage tourne **à vide**.

**Cette US reste mesurable malgré cela**, et c'est ce qui la distingue de
task-194 : elle fait passer le listage de *deux requêtes, dont un scan complet
de table* à **zéro requête**. Le gain mesuré est donc réel et observable — il
est simplement **minoré**, puisque la part de coût qui manque au banc
(comptage) est justement celle qu'on supprime aussi. **L'erreur est du côté
sûr : on sous-promet.**

Le rapport de mesure **doit le dire** en toutes lettres, sans quoi le chiffre
sera lu comme un plafond alors qu'il est un plancher. **task-267** corrige le
corpus ; si elle est livrée avant, refaire la mesure et publier les deux.

### Hors scope, explicitement

- **Le coût du calcul lui-même** → task-194. Ne pas optimiser les requêtes de
  fil ici : ce serait faire deux fois le même travail, mal.
- **Câbler un mode de vue dans `client-blazor`** → US séparée si le besoin est
  confirmé. Blazor reste inchangé.
- **Semer des fils dans le corpus du banc** → **task-267**. Changer à la fois la
  chose mesurée et l'instrument de mesure dans le même run rendrait la mesure
  inopposable — c'est le travers que task-264 a dû traiter pour la chauffe.
- **Le réglage `MailViewMode` côté serveur** : il reste stocké et restitué tel
  quel, non consulté. Cette US ne lui donne pas de rôle nouveau.
- L'identité des mails → task-179.

## Definition of Done

- [ ] Build passe sur les 3 repos (0 erreur)
- [ ] Tests passent (0 échec, hors flaky pré-existants documentés)
- [ ] Test backend : appel **sans** le paramètre → les deux requêtes de fil sont
      émises et la réponse porte `ThreadCount` / `IsThreadRoot` **identiques** à
      aujourd'hui (non-régression du défaut compatible)
- [ ] Test backend : appel **déclarant ne pas en avoir besoin** → **aucune**
      requête de fil émise, vérifié par assertion sur le repository (compteur
      d'appels ou substitut strict), **pas** seulement sur la réponse
- [ ] Ce second test **doit échouer sur le code actuel** — le vérifier
      explicitement et le consigner
- [ ] Test Angular : en mode `List` le paramètre est envoyé ; en mode
      `Conversation` il ne l'est pas (ou l'inverse selon la forme retenue) —
      assertion sur l'URL appelée
- [ ] Test Mobile : idem, assertion sur l'URL appelée
- [ ] Test de non-régression d'affichage : en mode `Conversation`, compteurs
      affichés et repliement **identiques** avant/après, sur un jeu de données
      avec `In-Reply-To` et `References` variés
- [ ] **`client-blazor` non modifié** — vérifiable : `git diff` vide sur
      `Client/Blazor`
- [ ] Le harnais k6 sait émettre les **deux** formes d'appel (avec et sans le
      paramètre) — sans cela la mesure « après » serait identique à « avant »
- [ ] **Mesures chiffrées avant/après** consignées dans la task, obtenues sur le
      banc (tasks 173/174) : latence p50/p95 du listage de dossier en mode
      `List` **et** en mode `Conversation`, plus le nombre de requêtes base par
      page dans chaque mode
- [ ] Le rapport de mesure **énonce** que le corpus du banc ne porte aucun fil,
      donc que le gain publié est un **plancher** et non un plafond
      (cf. task-267)
- [ ] Le mode `Conversation` ne montre **aucune** dégradation mesurable
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

1. Démarrer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. Démarrer le front legacy : `cd Client/Angular/front && npm start`
3. Se connecter avec une boîte de test MSSanté de formation contenant **des
   fils de discussion** (au moins un fil de 3 messages ou plus).
4. **Mode `List` (défaut)** — ouvrir Paramètres, vérifier que le mode
   d'affichage est bien « Liste ». Ouvrir la boîte de réception.
   **Attendu** : la liste s'affiche exactement comme avant — un message par
   ligne, aucun badge « N messages ». Dans les journaux serveur (Seq), filtrer
   sur le listage : **aucune** requête de comptage de fil ne doit apparaître.
5. **Mode `Conversation`** — basculer le réglage, revenir à la boîte de
   réception. **Attendu** : les fils sont repliés, le badge « N messages »
   s'affiche avec **les mêmes valeurs qu'avant le correctif** (les noter à
   l'étape 4 d'une exécution de référence, ou comparer à une capture).
   Déplier un fil : mêmes messages, même ordre.
6. **Blazor inchangé** — ouvrir le client Blazor sur la même boîte.
   **Attendu** : les badges de fil s'affichent comme avant, quel que soit le
   réglage de mode de vue. C'est le point de non-régression du repo hors
   périmètre.
7. **Mobile** — répéter les étapes 4 et 5 sur `client-mobile`.
8. **Ordre de grandeur** — sur une boîte volumineuse, comparer subjectivement le
   temps d'affichage de la liste en mode `List` avant/après. La mesure opposable
   est celle du banc (DOD), pas celle-ci.

**Données de test** : boîte de formation MSSanté, aucun patient réel, aucun INS.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors exigence DSR spécifique — sujet de performance ;
  contribue indirectement à l'utilisabilité du volet MSSanté
- **Exigences DSR honorées** : non applicable — aucune exigence fonctionnelle
  nouvelle, aucun changement d'affichage
- **INS** : non applicable — aucune donnée d'identité manipulée ; le comptage de
  fils repose sur les en-têtes RFC 5322 (`Message-ID`, `In-Reply-To`,
  `References`), jamais sur l'identité du patient
- **Authentification PS** : PSC / e-CPS, niveau eIDAS substantiel — inchangée,
  hors périmètre
- **Habilitations** : inchangées. **Point de vigilance** : le paramètre ne doit
  **jamais** élargir le périmètre de données lues — il ne peut que **retirer**
  du calcul, jamais en ajouter. Un paramètre qui ferait lire plus serait un
  défaut de conception, pas une option
- **Interop CI-SIS** : non applicable — aucun format d'échange métier touché
- **Tracé PGSSI-S** : inchangé. Ne pas supprimer de journalisation existante en
  supprimant le calcul ; l'absence de calcul peut être tracée en `Debug`, sans
  objet de message ni contenu
- **Consentement patient** : non applicable — aucun partage, aucune alimentation
  DMP / Mon Espace Santé
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — cible inchangée
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau. Le correctif
  **réduit** le volume de données lues côté serveur (moins de lignes
  matérialisées), il n'en élargit aucun périmètre

## Branches

- `api-mail` (pushed) : feat/task-266-compteurs-fils-a-la-demande — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-266-compteurs-fils-a-la-demande
- `client-mobile` (pushed) : feat/task-266-compteurs-fils-a-la-demande — https://github.com/codengine-technologies/HealthPlatform.Client.Mobile/tree/feat/task-266-compteurs-fils-a-la-demande
- `client-angular` (code-only) : la forge écrit sur la branche actuellement checked out dans `Client/Angular/` — instantané au `/start` : **`feature/nova-rewriting-mss`**, 2 fichiers déjà modifiés (travail humain en cours, non touché). L'humain gère branche, commit, push et PR TFS.
- `dtos-mss` (pushed, auto-inclus) : feat/task-266-compteurs-fils-a-la-demande — aucune modification attendue (le paramètre est de requête, pas de contrat DTO)

Préfixe `feat/` : ajout d'un paramètre de requête au contrat, avec défaut
compatible.

> ⚠️ **Ordre** : l'ordre recommandé était **267 avant 266**, pour que la mesure
> banc porte sur un corpus contenant des fils. 266 est lancée d'abord sur
> décision humaine — sa mesure reste valide mais **minorée**, ce que la section
> « Ce que la mesure peut et ne peut pas montrer » impose de dire dans le
> rapport.

## Develop log (2026-08-22)

Livré : `api-mail` `0e675f4`, `client-mobile` `ff941d3`, `client-angular`
code-only (3 fichiers, non committés — l'humain gère TFS).

### Le mécanisme, et ce qu'il refuse de faire

Paramètre de requête `includeThreadCounts`, **pas** la lecture de `MailViewMode`
côté serveur. La raison est celle du task file, et elle tient : `client-blazor`
n'a **aucune** notion de mode de vue et consomme `ThreadCount` en permanence —
un court-circuit piloté par le réglage lui ferait perdre ses badges pour tout
utilisateur en mode `List`, c'est-à-dire **par défaut tous**. Une préférence
d'**affichage** d'un client ne pilote pas un **calcul** serveur partagé par
trois clients.

**Défaut compatible** : absent ⇒ comportement d'aujourd'hui à l'identique.
L'économie est **opt-in**, jamais imposée.

### Deux décisions prises en cours de route

1. **Court-circuit sur les DEUX chemins de lecture**, pas seulement le chemin
   IMAP décrit par la task. Le faire sur un seul ferait dépendre le gain du
   **mode de connexion**, de façon invisible pour l'appelant : il demande la même
   chose et paie deux prix selon un état qu'il ne contrôle pas.
2. **Valeurs neutres explicites** quand le calcul est court-circuité
   (`ThreadCount = 1`, `IsThreadRoot = true`, `IsPartOfThread = false`) plutôt
   que les défauts de sérialisation. Un `ThreadCount = 0` serait un piège pour un
   futur consommateur : il ne peut pas distinguer « pas calculé » de « fil
   vide ». Ces valeurs sont exactement celles que le comptage rend pour un
   message hors fil (task-268).

### Le harnais k6 — sans lui, la mesure serait vide

`JOURNEY_THREAD_COUNTS` expose les **deux jambes**. C'est indispensable et non
cosmétique : le défaut serveur étant **compatible**, un appelant muet continue de
payer le calcul, donc la mesure « après » aurait été **identique** à la mesure
« avant ». Défaut `1` = l'appel d'avant la task, à l'identique — ce qui rend la
jambe « avant » comparable.

### Tests

**Backend — 4**, dont le cœur : « **zéro** requête émise », assertionné sur le
**repository** (`DidNotReceive()`) et non sur la réponse. Une assertion sur la
réponse passerait sur du code qui calcule puis jette. **Constaté RED avant
implémentation** : la surcharge n'existait pas — erreur de compilation `CS1739`
sur les trois appels nommés.

**Clients — 2 par client**, tous deux sur l'**URL appelée** : c'est elle qui
porte la déclaration. Un test sur le résultat passerait alors même que le client
aurait cessé de demander le court-circuit.

| Suite | Résultat |
|---|---|
| `mss.mail.application.tests` | **2 163 / 2 163** ✅ |
| `mss.mail.domain.tests` | **136 / 136** ✅ |
| `mss.mail.infrastructure.tests` | **464 / 464** ✅ |
| `mss.mail.integration.tests` | **412 / 428** (16 skipped, 0 échec) ✅ |
| `mss.mail.api.tests` | **665 / 665** au second passage ✅ |
| `client-mobile` (build + tests) | build OK, **763 / 763** ✅ |
| `selftest.sh` du harnais | 94 JS + 297 Python, 0 échec, **0 SKIP** ✅ |

**Flaky pré-existant rencontré** :
`FlagsmithFeatureFlagServiceTests.RefreshFailure_LogsOncePerWindow_AndIncrementsFailureCounter`
— test de fenêtre temporelle, sans rapport avec cette task, vert au second
passage.

### `client-blazor` — non modifié, et c'est vérifiable

`git diff` vide sur `Client/Blazor` : il ne passe pas le paramètre, donc il
continue de recevoir les compteurs. C'est le critère de DOD qui protège son
affichage.

### Ce qui reste dû, et pourquoi la mesure sera minorée

L'ordre recommandé était **267 avant 266**. Lancée d'abord, la mesure banc de
cette task portera sur un corpus **sans fils** (`BuildMime` ne pose ni
`In-Reply-To` ni `References`) : le gain publié sera un **plancher** — deux
requêtes dont un scan complet de table ramenées à **zéro**, mais sans la part de
coût du comptage lui-même, qui est vide sur ce corpus. La section « Ce que la
mesure peut et ne peut pas montrer » impose de le dire dans le rapport, et c'est
ce qui sera fait.

## Simplify log (2026-08-22)

Passe qualité — `api-mail` `fe89440`, `client-angular` code-only (non committé).

- **Réutilisation, côté Angular** — `threadCountFor()` répétait la condition de
  mode que `needsThreadCounts()` porte désormais. La règle « cet écran
  affiche-t-il les fils ? » n'a plus qu'**une** définition, et c'est elle qui
  décide à la fois ce qu'on **demande** au serveur et ce qu'on **affiche**. Deux
  copies dériveraient — et on redemanderait un calcul qu'on jette, c'est-à-dire
  le défaut même que cette task corrige.
- **Trou de couverture repéré, puis fermé** — le chemin IMAP pose les valeurs
  neutres explicitement (`ApplyNoThreadFlags`), le chemin base les obtient
  autrement (dictionnaires vides + défaut de `GetThreadCount`). Deux mécanismes,
  un seul résultat attendu, **et rien ne le surveillait** : c'est la forme de
  divergence silencieuse que task-268 vient de fermer, rouverte par un chemin
  neuf. Test ajouté, **mutation vérifiée** (ne plus poser les valeurs neutres
  côté IMAP → rouge).

### ⚠️ Une première version de ce test ne prouvait rien

Écrite d'abord dans le projet **unitaire**, elle devait **stubber** la réponse du
chemin base — donc elle **affirmait** la valeur attendue au lieu de la
**constater**, et comparait mon propre stub à l'autre chemin. Retirée et
réécrite dans le projet d'**intégration**, contre le **vrai** repository. Un
test qui pose lui-même la réponse qu'il vérifie est pire qu'une absence de test :
il donne le vert.

Re-validation : build 0 erreur / **0 avertissement** ; api **665/665**,
application **2 163/2 163**, domain **136/136**, infrastructure **464/464**,
integration **413/429** (16 skipped, 0 échec). `dtos-mss` non touché.

## Sonar log (2026-08-22)

### KPIs qualité — baseline → final

| Condition | Baseline | Final | Seuil | Verdict |
|---|---|---|---|---|
| `new_coverage` | 88,3 % | **88,3 %** | ≥ 80 | ✅ |
| `new_duplicated_lines_density` | 0,058 % | **0,058 %** | ≤ 3 | ✅ |
| `new_security_hotspots_reviewed` | 100 % | **100 %** | 100 | ✅ |
| `new_violations` | 68 | **68** | 0 | ❌ |
| **Quality Gate** | **ERROR** | **ERROR** | — | inchangé |

### Zéro finding introduit

Un seul finding porte sur un fichier de la task : `csharpsquid:S138` sur
`LoadBulkContentLookupsAsync` (106 lignes > 80) — **le même que sur task-268**,
et **pré-existant** pour la même raison. Vérifié plus finement cette fois :

- la méthode est **identique au hash près** entre `develop` et la branche
  (`md5sum` sur le corps extrait : `47ab6277…` des deux côtés) ;
- `git diff origin/develop -- MailRepository.cs | grep -c LoadBulkContentLookupsAsync`
  renvoie **0**.

Elle n'entre dans la fenêtre de new code que parce que les modifications en
amont dans le fichier ont décalé sa ligne de déclaration. **Non corrigée**, même
raison que pour task-268 : scinder une méthode qu'on ne touche pas gonflerait le
diff pour zéro bénéfice à cette US. Elle mérite sa propre passe.

Les 67 autres viennent de tasks **déjà mergées** — `report.py`,
`journey-model.js`, `journey.js` (harnais des tasks 263/264) et quelques
fichiers backend antérieurs. Les fichiers JS du harnais modifiés par cette task
(`lib/api.js`, `lib/config.js`) n'ont produit **aucun** finding.

### Suites en Release (configuration du scan)

domain **136/136**, application **2 163/2 163**, api **665/665**,
integration **413/429** (16 skipped, 0 échec) ; infrastructure 463/464 = le
flaky `MailReadObjectCountTests` caractérisé lors de task-216 (vert en
isolation, alterne en suite complète, **présent sur develop**).

## Lint Angular log (2026-08-22)

Mode A, `Client/Angular/front/`, base `origin/next`, **code-only** (aucune
opération git d'écriture).

| Étape | Résultat |
|---|---|
| Lint baseline (`mss-lib`) | **1 erreur**, 36 warnings |
| Itération 1 — auto-fix ESLint | **0 erreur**, 36 warnings |
| Build `mss-lib` | ✅ |
| Tests `mss-lib` | **317 / 317** (40 fichiers), dont les 2 tests de task-266 |

**L'unique erreur était la mienne** : `jsdoc/require-param` — le JSDoc de
`getEmails` ne déclarait pas `includeThreadCounts`. Corrigée par l'**auto-fixer**,
donc **pas d'entrée dans `conventions/angular.md`** : le protocole exclut
explicitement les fixes gratuits. Les 36 warnings restants sont de la dette
pré-existante (`max-lines`, `complexity`, `jsdoc/require-example`), acceptée
best-effort.

### ⚠️ Le build de production échoue, et ce n'est pas cette task

`nx affected -t build` échoue sur `mss:build:production` :
`apps/mss/src/environments/environment.prod.ts` **n'existe pas**.

**Établi, pas supposé** : ce fichier **existe sur `origin/next`** et **pas sur
`HEAD`** (`feature/nova-rewriting-mss`) — il a été supprimé sur la branche de
travail humaine. Et la **contre-épreuve est faite** : en mettant mes trois
fichiers de côté (`git stash push` ciblé) puis en relançant le build avec
`--skip-nx-cache`, **l'échec est identique**. `mss-lib`, où vit mon code, se
construit sans erreur.

C'est du travail humain en cours sur `client-angular` : mode code-only, la forge
n'y touche pas.

### ⚠️⚠️ DÉFAUT D'OUTILLAGE — le filtre de scope MSS est INERTE

La commande du playbook,
`npx nx affected -t lint --base=… --head=HEAD --parallel=3 --projects=tag:scope:mss`,
**ne restreint rien** : Nx passe `--projects` **à l'exécuteur ESLint**, où il ne
signifie rien. La preuve est dans la sortie — `> nx run prescription:lint
--projects=tag:scope:mss`, puis « Running target lint for **11 projects** ».

Conséquence observée ici : l'auto-fixer a écrit dans **`apps/weda2`** (5
fichiers du module `booking/daily`) et dans deux fichiers `libs/mss` sans
rapport avec la task — **hors charte MSS**, que la forge s'impose précisément
pour ne pas toucher à la dette d'autrui.

**Les 7 fichiers ont été annulés** (`git checkout --`), l'arbre est revenu à
l'état d'avant : les 2 `environment.ts` de l'humain et les 3 fichiers de
task-266. Le lint reste à **0 erreur** après annulation.

Détail aggravant : les fixes en question ajoutaient des balises `@example`
**vides**, qui ne résolvent même pas le warning (il devient « Missing @example
**description** »). Du bruit dans le diff d'autrui, sans gain.

**À corriger dans `agents/lint-angular.md`** — la forme correcte est
`nx run-many -t lint --projects=tag:scope:mss` (ou `-p`), pas `affected
--projects`. Non fait ici : c'est le plan de contrôle de la forge, pas le
périmètre de cette US.

## Lint mobile log (2026-08-22)

Mode A, `Client/Mobile/`, branche `feat/task-266-compteurs-fils-a-la-demande`.

**Baseline : « All files pass linting. »** — 0 erreur, 0 warning. Aucune
itération d'auto-fix n'était nécessaire, donc **aucun commit** de lint (le
playbook ne commite que des fixes ; il n'y en a pas eu).

Le filet anti-régression avait déjà été passé au `/develop` sur ce repo :
`npm run build` OK, **763 / 763** tests (`ChromeHeadless`), dont les 2 tests
d'URL de task-266.

## Visual verify log (2026-08-22)

Skip propre — aucun **écran** `client-mobile` touché. La modification porte sur
le service HTTP (`mss-api.service.ts`) et sur la dérivation du besoin dans
`inbox.page.ts` ; **aucun gabarit, aucun style, aucun composant d'affichage**
n'a changé, et le task file ne porte pas de `## Stitch design log`.

C'est cohérent avec le DOD de la US : « Aucun changement d'affichage nulle
part » — en mode Liste l'écran était **déjà** identique puisque les champs y
étaient ignorés. Aucun serveur lancé, aucune capture.

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/198 — label `awaiting-human-merge`
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/62 — label `awaiting-human-merge`
- `client-angular` : **code-only** — l'humain gère commit/push TFS et ouverture de PR. Fichiers modifiés par la forge sur la branche `feature/nova-rewriting-mss` :
  - `front/libs/mss/src/core/services/mss-api.service.ts`
  - `front/libs/mss/src/core/services/mss-api.service.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.ts`

  ⚠️ Les deux `environment.ts` modifiés dans le même arbre sont du **travail
  humain antérieur**, pas de la forge. Ne pas les confondre au moment de
  committer.
- `dtos-mss` : aucune modification, pas de PR (branche auto-incluse restée vide)
- Staging : task menée hors run `/forge` — aucune branche staging.

## Code Review Summary

**APPROVED** — 0 blocage, 1 suggestion.

Contrat étendu par un paramètre à **défaut compatible**, vérifié par un test
dédié. Le paramètre ne peut que **retirer** du calcul, jamais en ajouter :
aucun élargissement de périmètre de données lues (vigilance habilitations de la
US). Court-circuit symétrique sur les deux chemins, valeurs neutres cohérentes
avec task-268, et leur convergence est testée contre le vrai repository.

**`client-blazor` non modifié et vérifié tel** : `git diff` vide, repo sur
`develop`.

**Suggestion non bloquante** : la construction de la chaîne de requête est
écrite trois fois (k6, Angular, Mobile). Trois langages, trois dépôts — aucune
factorisation possible sans créer un couplage pire que la duplication. Signalé
pour mémoire.

### DOD

| Critère | État |
|---|---|
| Build passe sur les 3 repos | ✅ (api-mail 0 avertissement) |
| Tests passent | ✅ hors flakies pré-existants caractérisés |
| Test : appel **sans** paramètre → deux requêtes émises, champs identiques | ✅ |
| Test : appel déclarant ne pas en avoir besoin → **aucune** requête, assertion sur le **repository** | ✅ |
| Ce second test **échoue sur le code actuel** | ✅ `CS1739` — la surcharge n'existait pas |
| Test Angular : assertion sur l'URL | ✅ 2 tests |
| Test Mobile : assertion sur l'URL | ✅ 2 tests |
| Non-régression d'affichage en mode `Conversation` | ✅ champs inchangés quand le paramètre est absent ou `true` |
| **`client-blazor` non modifié** — `git diff` vide | ✅ |
| **Mesures chiffrées avant/après** sur le banc | ⏳ **humain** — cf. « Ce que la mesure peut et ne peut pas montrer » |
| Le mode `Conversation` ne montre aucune dégradation | ⏳ **humain**, même campagne |
| Le rapport énonce que le gain est un **plancher** (corpus sans fils) | ⏳ à faire au moment de la campagne |
| Aucune donnée de santé en clair dans les logs | ✅ aucun log ajouté |

## Merged (2026-08-22)

**Date** : 2026-08-22 — `/merge 266 --i-tested` (HAG, règle 10).

| Repo | PR | Commit squash sur `develop` |
|---|---|---|
| `api-mail` | [#198](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/198) | `5c53458` |
| `client-mobile` | [#62](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/62) | `d182ba9` |
| `dtos-mss` | aucune PR — branche auto-incluse sans commit | — |
| `client-angular` | code-only — **reste à la main de l'humain** (commit/push TFS) | — |

**CI `develop`** : `api-mail` ✅ verte. `client-mobile` ❌ — **voir ci-dessous**.

### ⚠️ Gate 4 (CI verte) EXPLICITEMENT OUTREPASSÉ sur `client-mobile`

La PR #62 était rouge au moment du merge, et le merge a quand même eu lieu.
C'est une décision, pas un oubli, et voici sur quoi elle repose.

**Les 11 étapes de build sont vertes** — `Install dependencies`, `Build web
assets`, `Set up Android SDK`, `Sync Capacitor Android`, `Build debug APK`.
**Seule `Upload debug APK` échoue** :

```
Failed to CreateArtifact: Artifact storage quota has been hit.
Unable to upload any new artifacts. Usage is recalculated every 6-12 hours.
```

C'est une condition de **facturation du compte GitHub**, pas un défaut de code :
l'APK est bien produit (« With the provided path, there will be 1 file
uploaded »), c'est son **dépôt** qui est refusé. Constaté sur **trois** runs —
deux sur la PR, un sur `develop` après merge — avec la même étape et la même
cause.

**Ce que cela implique** : la CI de `client-mobile` restera rouge sur toutes les
branches jusqu'à ce que le quota se recycle (6 à 12 h selon GitHub) ou soit
relevé. Ce n'est **pas** un signal exploitable pendant cette fenêtre, et il ne
faut pas le confondre avec une régression. Purger les artefacts anciens du dépôt
ou augmenter le quota rend le signal utilisable de nouveau.

**Nettoyage** : refs distantes supprimées sur `api-mail`, `client-mobile` et
`dtos-mss` ; branches locales conservées. Aucune branche staging (hors run
`/forge`).

### Reste à la main de l'humain

1. **`client-angular`** — 3 fichiers non committés sur `feature/nova-rewriting-mss` :
   `mss-api.service.ts`, `mss-api.service.spec.ts`, `mail-list.component.ts`.
   ⚠️ Les deux `environment.ts` du même arbre sont du travail humain antérieur,
   pas de la forge.
2. **Le build de production Angular est cassé** sur cette branche
   (`apps/mss/src/environments/environment.prod.ts` absent alors qu'il existe sur
   `origin/next`) — antérieur à cette task, contre-épreuve faite, mais il
   bloquera la PR TFS.
3. **Les mesures banc** (DOD) restent dues, et seront **minorées** tant que
   task-267 n'a pas donné au banc un corpus porteur de fils : le gain publié sera
   un **plancher**. Le rapport devra le dire.

### Dette d'outillage constatée pendant le cycle, non corrigée

Le **filtre de scope MSS de `/lint-angular` est inerte** :
`nx affected -t lint --projects=tag:scope:mss` passe `--projects` à l'exécuteur
ESLint, où il ne signifie rien — 11 projets ont été lintés et auto-fixés, dont
`apps/weda2`. Les 7 fichiers hors charte ont été annulés. Correction à porter
dans `agents/lint-angular.md` : `nx run-many -t lint -p tag:scope:mss`.
