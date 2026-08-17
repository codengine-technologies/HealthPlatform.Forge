# todo-task-260.md — L'envoi coûte 1,3 s quelle que soit la population : décomposer avant de corriger, parce que deux tentatives ont déjà échoué

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune. **task-238** a tenté deux fois de corriger ce coût et
échoué deux fois — c'est précisément l'argument pour instrumenter d'abord.
**Priorité**: **1** — **seule étape hors grille du parcours du médecin**, et
**premier poste de coût serveur** du tir à 500 (25,1 %). Tant qu'elle n'est pas
décomposée, toute correction sera écrite sur une intuition.

## Objective

Savoir **où passent les 1,3 seconde** d'un envoi de message, phase par phase, de
sorte que la prochaine US d'optimisation vise une cause mesurée.

C'est une US **d'instrument, pas d'optimisation**. Elle ne rend rien plus rapide.

## Ce qui est établi — tir `journey-500-esc` du 2026-08-14

Escalier 100 / 200 / 500 médecins, banc distant, K=1, 295 325 requêtes,
0,004 % d'erreur.

| Palier | p50 envoi | p95 envoi | Cible p50 / p95 |
|---|---|---|---|
| 100 médecins | **1 305 ms** | 1 993 ms | 1 000 / 3 000 |
| 200 médecins | **1 270 ms** | 1 963 ms | 1 000 / 3 000 |
| 500 médecins | **1 302 ms** | 2 004 ms | 1 000 / 3 000 |

**Le coût est RIGOUREUSEMENT PLAT sur un facteur 5 de population.** Ce n'est donc
pas un effet de charge, ni une file, ni une contention : c'est un **coût fixe
payé à chaque envoi**. C'est aussi ce qui rend le défaut réparable — il ne
dépend d'aucune condition de banc.

**Ce que ça pèse** : **6 085 s de temps serveur sur 4 031 appels**, soit
**25,1 %** du temps serveur total du palier 500 — le premier poste, devant le
tableau de bord (23,5 %) et la page d'en-têtes (11,5 %).

**Ce qui a déjà été fait, et n'a pas suffi** : task-231 (la connexion SMTP n'est
plus rouverte à chaque message), task-238 (la connexion retenue est entretenue,
la sonde quitte le chemin nominal), task-241 (le keep-alive agissait sur la
mauvaise horloge). Trois corrections, et le coût n'a pas bougé.

### ⚠️ La piste que l'analyse Seq désigne — à examiner en premier, pas à croire

**12 482 `SmtpCommandException` pour 4 031 envois**, soit **~3,1 par envoi** :
c'est la **famille d'exceptions la plus nombreuse de tout le tir**, devant les
extinctions de session.

Le volume suit le **nombre d'appels**, pas la charge — c'est le test que le skill
prescrit pour distinguer un coût par requête d'un incident. Rapproché d'un coût
**plat sur un facteur 5 de population**, cela désigne un chemin de code exercé à
chaque envoi, qui lève et rattrape.

⚠️ **Ce n'est PAS une cause établie.** Une exception rattrapée peut coûter très
peu, et rien ne relie aujourd'hui ces 12 482 levées aux 1,3 seconde. C'est une
**piste**, et la décomposition doit précisément permettre de la confirmer ou de
l'écarter — pas de la présumer. Une US écrite sur « il faut supprimer ces
exceptions » serait exactement l'erreur de task-222.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que c'est encore le SMTP.** Trois corrections successives ont
  visé cette hypothèse. Si elle était la bonne, le chiffre aurait bougé.
- **Ne pas présumer que c'est l'archivage dans « Messages envoyés ».** C'est le
  candidat suivant le plus évident, donc celui dont il faut se méfier — et
  `118c3f4` a déjà changé son comportement une fois.
- **Ne pas présumer que le p50 et le p95 ont la même cause.** 1,3 s au p50 contre
  2,0 s au p95 : la queue peut appartenir à une phase différente de celle qui
  domine la médiane.
- **Ne pas optimiser en passant.** Si une évidence saute aux yeux, la consigner
  comme finding et la traiter dans une US **mesurée**. Cette EPIC a annulé
  task-222 pour avoir fait l'inverse.

## Ce que la US doit livrer

Pour l'envoi, le pendant de ce que task-245 a livré pour l'enrichissement et
task-252 pour le téléchargement d'une pièce jointe : un **périmètre par envoi**,
décomposé en phases nommées, publié à côté de l'enveloppe.

Les phases à distinguer sont celles qui appellent des remèdes différents :
**obtention de la session SMTP**, **négociation TLS** si elle a lieu,
**transmission du message**, **acquittement du serveur**, **archivage dans
« Messages envoyés »**, et **le reste** par différence.

Plus le **nombre d'allers-retours vers le serveur mail par envoi** — le
dénominateur sans lequel une durée ne dit pas si elle vient du volume d'échanges
ou de leur coût unitaire. C'est la leçon de task-243, task-256 et task-258 :
c'est ce compteur qui a permis, sur l'écriture, de trancher entre file et
travail.

## Definition of Done

- [ ] Build passe (0 erreur), tests passent (0 échec)
- [ ] Un périmètre par envoi publie ses **phases**, chacune sommable et
      comparable d'un tir à l'autre, plus **le reste** par différence
- [ ] Un compteur donne le **nombre d'allers-retours vers le serveur mail par
      envoi** — réutiliser `mssante_mail_server_solicitations_total` (task-225)
      plutôt que d'en créer un autre, si son périmètre le permet
- [ ] `report.py` publie la **phrase attribuable** : « sur les X ms d'un envoi,
      A ms sont l'obtention de session, B ms la transmission, C ms l'archivage… »
- [ ] **Hors périmètre, rien ne coûte** : sans scope actif, ni allocation ni série
- [ ] Une absence de donnée écrit **« non relevé »**, jamais un zéro
- [ ] Tests unitaires de la décomposition, dont un cas « session réutilisée »
      (aucune ouverture) et un cas « archivage absent »
- [ ] **Aucune donnée de santé dans les étiquettes** : ni INS, ni adresse de
      destinataire, ni objet de message — littéraux d'un ensemble fini,
      **vérifié par test**
- [ ] **Contre-épreuve** : un tir `journey` à au moins deux paliers, et le
      rapport **nomme la phase dominante**. Si la décomposition n'explique pas
      les 1,3 s, le **dire** — c'est un résultat, et il désigne alors une phase
      non instrumentée

## Manual Test Plan

- Monter le banc (skill `loadtest-skill`) — **contrôler d'abord à qui appartient
  le CPU**, et que les **UID des boîtes commencent à 1**
- Seeder une petite population, purger, préchauffer
- Lancer un tir `journey` à deux paliers
- **Ce qu'il faut voir** dans le rapport : la décomposition de l'envoi et sa
  phrase attribuable, avec le nombre d'allers-retours par envoi
- Envoyer un message depuis l'application : il doit partir normalement, et une
  copie doit apparaître dans « Messages envoyés »
- Vérifier dans Seq qu'aucune étiquette ne porte d'adresse ni d'objet de message

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — observabilité interne
- **Exigences DSR honorées** : aucune — aucun changement fonctionnel
- **INS** : ⚠️ le chemin instrumenté transporte des **comptes rendus porteurs
  d'INS**. Le périmètre ne publie que des **durées**, des **nombres** et des
  **noms de phases** pris dans un ensemble fini : aucune adresse, aucun objet,
  aucun identifiant
- **Interop CI-SIS** : volet transport MSSanté — ⚠️ **l'intégrité du message
  remis est bloquante** : l'instrumentation observe, elle ne doit rien changer au
  contenu transmis ni à l'archivage
- **Habilitations** : inchangées
- **Authentification PS / Consentement** : inchangés
- **Tracé PGSSI-S** : ⚠️ l'envoi est un acte tracé ; l'instrumentation ne doit ni
  masquer ni dupliquer une entrée d'audit existante
- **Hébergement HDS** : le coût de l'instrument doit être négligeable en
  production — critère « hors périmètre, rien ne coûte » ci-dessus
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : feat/task-260-decomposer-envoi — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-260-decomposer-envoi
- `dtos-mss` (pushed, auto-inclus) : feat/task-260-decomposer-envoi — aucun contrat attendu

## Develop log — 2026-08-14

**Livré** : `SendOperationScope` (6 phases : garde d'opposition, construction
MIME, obtention de session, transmission+acquittement, archivage Sent
optionnelle, reste par différence), **imbriquable** — le contrôleur ouvre le
périmètre englobant envoi+archivage (la durée que paie le médecin), le `Begin`
de `SmtpService` devient inerte dessous. Alimentation aux 4 sites naturels + 
`AppendToSentAsync`. `report.py` : section « Où part le temps d'un envoi »,
phrase attribuable, `archive_sent` « non relevé » quand absente.

**Compteur d'allers-retours** : déjà en place (`solicitationRecorder`, task-225)
— réutilisé, pas dupliqué.

**Tests** : 7 C# éprouvés par mutation (6/7 rouges sans publication — après DEUX
faux positifs de protocole corrigés : mutation non compilable, puis binaire de
test non reconstruit), 6 Python. **Collision de parallélisme** : 4 classes de
test exercent désormais l'envoi et polluaient les captures — rangées dans
`MailMetricsCaptureCollection` (le mécanisme posé par task-256, deuxième paire
de classes confirmée).

## Simplify log — 2026-08-14

Un exotisme retiré (délégué à retour de référence → style maison des scopes).
**Consigné sans traiter** : 5ᵉ copie du helper `Capture` de tests — les 4 autres
préexistent, hors charte de cette passe. 7 tests verts après.

## Sonar log — 2026-08-15

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| **Quality Gate** | OK | **OK** | = |
| Bugs / Vulnérabilités | 0 / 0 | **0 / 0** | = |
| Issues sur les fichiers touchés | — | **2, toutes préexistantes** (S3604 sur `SmtpService.cs`, lignes de task-231 — vérifié par `git blame`) | **dette introduite : zéro** |

Le code de cette task est **dans le périmètre analysé** (`src/Application`,
`src/Api`) : le verdict porte sur le livrable.

### 🟠 Finding découvert par le run de couverture — la vue « aujourd'hui » a une fenêtre aveugle nocturne

Le run Release a traversé minuit : **5 tests d'intégration rouges, tous des
filtres « aujourd'hui »**, et ils restent rouges rejoués après minuit —
**déterministes entre 00 h et 02 h locales**, chaque nuit.

**Cause lue dans le code de production** (`ImapService.cs:768`) :
`GetFolderNotSeenTodayAsync` filtre par `SearchQuery.DeliveredAfter(DateTime.Now.Date)`
— minuit **local** — pendant que l'INTERNALDATE IMAP des messages vit en UTC.
Entre 00 h et 02 h (UTC+2), « aujourd'hui » local n'a pas commencé en UTC : les
messages du début de nuit échappent au filtre.

**Aucun de ces fichiers n'est dans le diff de task-260** (vérifié) — flaky
**pré-existant**, jamais vu parce qu'aucun run n'était tombé dans la fenêtre.
Et c'est un **finding produit** autant qu'un flaky de test : un médecin de garde
qui ouvre sa vue « aujourd'hui » à 1 h du matin peut ne pas voir les messages
reçus depuis minuit. **À instruire en US** — non traité ici (hors périmètre).

## Lint log — 2026-08-15

**Skips propres** : `client-angular`, `client-mobile` non touchés
(`**Repos**: api-mail`), aucun écran mobile — `/lint-angular`, `/lint-mobile` et
`/verify-visual` sans objet.

## PRs

- `api-mail` (pushed) : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/190 — label `awaiting-human-merge`
- `dtos-mss` (pushed, auto-inclus) : **aucune PR** — branche sans commit

## Code Review Summary

**Verdict : APPROVED** — 12 fichiers (+802 lignes), 0 blocage, 0 suggestion.

| Contrôle | Résultat |
|---|---|
| Build | ✅ 0 erreur, 0 avertissement |
| Tests | ✅ **3 792 verts** — 6 rouges, TOUS pré-existants et caractérisés : 5 = fenêtre nocturne 00h–02h de la vue « aujourd'hui » (cause lue dans `ImapService.cs:768`, fichiers hors diff), 1 = `AiPromptHelperTests` (commit `411b289`) |
| DOD | ✅ 8 critères sur 9 — la contre-épreuve au banc (dernier critère) reste ouverte : elle exige un tir `journey`, à faire après merge |
| Quality Gate | ✅ OK — dette introduite **zéro** (2 issues sur fichiers touchés, toutes de task-231, vérifié par `git blame`) |

Revue détaillée dans le corps de la PR. Points saillants : périmètre imbriquable
(contrôleur = englobant, `SmtpService` = inerte dessous), `archive_sent`
optionnelle « non relevé » ≠ zéro, mutation 6/7 après correction de deux faux
positifs de protocole, collision xUnit réglée par `MailMetricsCaptureCollection`.

## Merged

**Date** : 2026-08-17 19:07 UTC — `/merge task-260 --i-tested` (HAG, règle 10 :
l'humain a testé et attesté avant merge).

| Repo | PR | Commit squash sur `develop` |
|---|---|---|
| `api-mail` | [#190](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/190) | `a96354e` |
| `dtos-mss` | aucune PR — branche auto-incluse sans commit | — |

- Six garde-fous passés avant merge : `--i-tested` présent, label
  `awaiting-human-merge` (pas `awaiting-us-completion`), `reviewDecision` vide,
  CI PR verte (`build` 1m46s), `mergeable = MERGEABLE / CLEAN`, arbres de travail
  propres sur `api-mail` et `dtos-mss`.
- Refs distantes `feat/task-260-decomposer-envoi` supprimées sur `api-mail` et
  `dtos-mss` (jamais `--delete-branch`). **Aucune branche locale n'existait**
  pour cette task sur les deux repos — rien à conserver ; `api-mail` était
  checked out sur la staging du run.
- `develop` synchronisé sur `api-mail` (fast-forward `4aff6ae..a96354e`, 12
  fichiers, +802 lignes) ; `dtos-mss` déjà sur `develop`.
- CI `develop` api-mail : ✅ **verte** — run
  [32058246607](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/32058246607)
  (`completed / success`, tête `a96354e`).
- Branche staging `forge/staging-task-260-264-20260814` **conservée** :
  task-261, 262, 263 et 264 du même run sont encore en `done-*`.
- **Reste ouvert** (hérité du DOD) : la contre-épreuve au banc du dernier
  critère exige un tir `journey` sur `develop` — à faire post-merge, hors
  périmètre de `/merge`.
