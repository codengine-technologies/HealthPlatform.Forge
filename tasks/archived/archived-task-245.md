# todo-task-245.md — Le pipeline d'enrichissement est le prochain poste de coût, et c'est une boîte noire

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-244** (chauffe lotie) — coordination forte : les deux US
se répondent. Celle-ci peut démarrer avant, elle gagne à être **mesurée** après,
quand un tir 500 termine enfin sa chauffe.
**Priorité**: **1** — c'est le goulot **G1** du premier tir 500, et le seul qui
rompe franchement : un abandon, pas une dégradation.

## Objective

Qu'on puisse répondre à « **où part le temps** dans l'enrichissement d'un
message ? » — exactement comme task-243 l'a fait pour la page d'en-têtes.

C'est une US **d'instrument, pas d'optimisation**. Elle ne rend rien plus rapide.
Elle rend le prochain correctif décidable, et surtout elle **empêche** de l'écrire
sur une intuition. Cette EPIC a déjà annulé une US applicative bâtie sur une cause
plausible et fausse (task-222) ; la règle qui en est sortie s'applique ici mot
pour mot.

## Ce qui est établi — et qu'il ne faut pas re-mesurer

Tir `journey-remote-n500` du 2026-08-09, 500 praticiens, mode distant :

| Fait | Mesure |
|---|---|
| La chauffe expire pour **500 médecins sur 500** | 98 messages en une requête, délai client 300 s |
| Coût unitaire, **borné par le bas** | **plus de 3 s par message** sous la concurrence de 100 médecins |
| p95 serveur de la route `enrich/sync` | **au moins 10 s** — le dernier bucket de l'histogramme sature |
| Le serveur travaille vraiment | `[CdaParsingService] Parsing completed` pendant et après l'abandon client |
| Ce n'est pas qu'une affaire de taille de lot | un `treatment` de **2 messages** a aussi expiré au palier 500 |

**Ce que la télémétrie ne sait PAS dire aujourd'hui** : la répartition de ces
secondes entre le **fetch IMAP du corps**, l'**extraction de l'archive XDM**, le
**parsing CDA**, la **génération d'embedding** et les **écritures base**. Sans
cette décomposition, tout remède est une devinette.

## Ce que la US doit livrer

Le pendant de `DbOperationScope` (task-243) pour le pipeline d'enrichissement :
un périmètre par message enrichi, découpé en phases nommées, **non ré-entrant**,
et **sans coût hors périmètre**. Plus un compteur du **nombre de messages par
requête**, pour distinguer « un message lent » de « trente messages moyens » —
deux remèdes sans rapport.

Les buckets d'histogramme doivent couvrir la **dizaine de secondes** : au-delà de
10 s le p95 actuel sature et ne dit plus rien, défaut constaté sur ce tir.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que c'est le parsing CDA.** C'est le candidat évident, donc
  celui qu'il faut se garder de désigner avant mesure. Le fetch IMAP distant
  (94 ms de latence injectée, corps d'environ 124 Ko) est tout aussi plausible.
- **Ne pas présumer que c'est le mode distant.** Le coût unitaire doit être mesuré
  **des deux côtés**, banc local et cluster : sinon on imputera au réseau ce qui
  appartient au traitement.
- **Ne pas optimiser en passant.** Si une évidence saute aux yeux, la consigner
  comme finding et la traiter dans une US suivante — mesurée. Une US d'instrument
  qui optimise ne peut plus prouver son propre effet.

## Definition of Done

- [ ] Chaque message enrichi produit une décomposition par phase (fetch IMAP,
      extraction XDM, parsing CDA, embedding, écriture base), en histogrammes
- [ ] Un compteur donne le **nombre de messages par requête** d'enrichissement
- [ ] Les buckets couvrent au moins **30 s** — plus aucune saturation de p95
- [ ] **Hors périmètre, rien ne coûte** : sans scope actif, ni allocation ni série
- [ ] `report.py` publie la décomposition et **la phrase attribuable** : « sur les
      X ms d'un enrichissement, A ms sont le fetch, B le parsing, C l'écriture »
- [ ] Si les phases ne somment pas au total, le rapport **le dit**
- [ ] Tests unitaires du scope + tests du rendu rapport, dont un cas « aucune
      donnée » qui écrit son absence au lieu de rendre une table vide
- [ ] Aucune donnée de santé dans les étiquettes : ni INS, ni contenu CDA, ni objet

## Manual Test Plan

- Monter le banc (skill `loadtest-skill`), en local **puis** en distant
- `POST .../emails/enrich/sync` sur 10 UID frais, puis lire la section
  « Où part le temps d'un enrichissement » du rapport
- Vérifier que la somme des phases explique le total à quelques pourcents près
- Contrôler dans Seq qu'aucune étiquette ne porte de donnée patient

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — observabilité interne
- **Exigences DSR honorées** : aucune
- **INS** : ⚠️ le pipeline manipule des CDA porteurs d'INS — **aucune étiquette de
  métrique ni aucun journal ajouté ne doit en contenir**. C'est le point de
  vigilance n°1 de cette US.
- **Authentification PS / Habilitations / Consentement / Interop CI-SIS** : inchangés
- **Tracé PGSSI-S** : métriques d'exploitation uniquement, corrélées par `traceId`
- **Hébergement HDS** : l'instrument doit être transposable à l'environnement cible
- **AIPD / impact RGPD** : inchangé — aucune donnée nouvelle collectée

## Branches
- `api-mail` (pushed) : feat/task-245-enrichment-phase-telemetry
- `dtos-mss` (pushed, auto-included) : feat/task-245-enrichment-phase-telemetry — no DTO change expected

## Develop log

- **api-mail** `feat/task-245-enrichment-phase-telemetry` — `b8f340a` (feat),
  `670cb50` (simplify), `86c03fb` (sonar). Poussé.
- **dtos-mss** — branche créée, **aucun commit** → pas de PR.

### Ce qui a été livré

**`EnrichmentOperationScope`** (nouveau) — le pendant de `DbOperationScope` : un
périmètre **par message**, `AsyncLocal`, **non ré-entrant**, **sans aucun coût hors
périmètre**. Phases `imap_fetch`, `xdm_extract`, `cda_parse`, `db_write`, plus
`assemble` (le reste, par différence).

**La phase `imap_fetch` est SEMÉE, pas accumulée** — et c'est la décision de
conception centrale. Le pipeline lit tout un sous-lot depuis IMAP (phase A, sous le
verrou de session) **puis** persiste (phase B, hors verrou) : les deux moitiés du
travail d'un même message sont séparées par le reste du lot, et aucun contexte
asynchrone ne les relie. La durée est donc mesurée en phase A, portée par
`FetchedMail`, et remise au périmètre à son ouverture. Sans cela le fetch —
candidat de premier plan, 94 ms de latence injectée sur ~124 Ko — paraîtrait
**gratuit**, et la somme des phases dépasserait le total.

**⚠️ L'embedding est hors périmètre, et c'est un fait VÉRIFIÉ, pas un oubli.** Il
s'exécute dans `AddNewMailConsumer`, déclenché par un `Publish` MassTransit que le
producteur **n'attend pas** (`MailMessagePublisher` → `IPublishEndpoint.Publish`) :
`enrich/sync` ne paie pas cette latence. Le compter dans le total aurait gonflé une
durée que le client n'attend jamais. Il est publié à part et le rapport l'écrit.

**Le p95 serveur saturait à 10 s** : les seaux par défaut de
`http.server.request.duration` s'arrêtent là, donc « p95 ≥ 10 s » n'était pas un
percentile mais la borne du dernier seau. Une vue OTel applique désormais le jeu
partagé des histogrammes maison (30 et 60 s en queue).

**Compteurs** `enrichment_requests_total` / `_request_messages_total` — ils
distinguent « **un** message lent » de « **trente** messages moyens ».

**Un point d'alimentation unique** pour les 8 sites d'exécution SQL (les deux
périmètres y sont alimentés ensemble) : c'est l'écart entre sites d'appel qui avait
produit le défaut d'instrumentation de task-214.

**`report.py`** — section « Où part le temps d'un enrichissement » avec la **phrase
attribuable**, le poste dominant, l'embedding rendu hors somme, et le reste
inexpliqué **écrit** au lieu d'être absorbé (écart négatif expliqué par le
`Task.Run` concurrent).

### Validation

- Build : **0 erreur**. Suite .NET : **3 702 réussis** (domain 136, application
  2 099, infrastructure 436, api 660, integration 371 + 16 ignorés).
- Harnais : **247 Python + 57 JS** verts (baseline pré-244 + 10 nouveaux).
- Nouveaux tests : **13** de périmètre (arithmétique, fetch semé, hors-périmètre
  muet, non-ré-entrance, survie à l'exception, traversée de `Task.Run`,
  cardinalité PGSSI-S) + **10** de rendu dont « aucune donnée » et le témoin
  « si le fetch domine, c'est LUI qui est nommé ».

### ⚠️ Pièges d'outillage rencontrés

- **`--artifacts-path` casse 10 tests d'architecture** (`SecretLiteralScanTests`,
  `MailContentWriterScanTests`, `EmbeddingOptionsConsistencyTests`, …) : ils
  scannent les sources/config par chemin relatif à la sortie de build. Ils sont
  **verts** avec la disposition standard. Ce n'est pas une régression.
- **3 échecs en Release sur une exécution, verts au re-run** — la famille de
  flakies pré-existants déjà documentée.

### Finding consigné — à NE PAS corriger ici

`BackgroundImapService.EnrichEmailsAsync` porte une **seconde implémentation
parallèle** du pipeline d'enrichissement (utilisée par `BackgroundSyncService`),
qui ne passe pas par `ImapService.EnrichEmailsAsync` et n'est donc **pas
instrumentée**. Le chemin **mesuré par le banc** (`enrich/sync` et le `treatment`
du parcours) passe bien par `ImapService` et est intégralement couvert. Étendre le
périmètre à cette copie est une US à part entière — et la US interdit d'optimiser
ou d'élargir en passant.

## PRs

- **api-mail** : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/177 — label `awaiting-human-merge`
- **dtos-mss** : aucun commit → **pas de PR** (branche vide, comme prévu)
- **Staging** : `forge/staging-task-244-252-20260809` — task-245 agrégée

## Code Review Summary

**APPROVED** — 10 fichiers, 0 blocage. Zéro issue Sonar sur les 7 fichiers C#.
Duplication projet 0,4 % → **0,3 %** (passe `/forge-simplify`).

| DOD | État |
|---|---|
| Décomposition par phase, en histogrammes | ✅ |
| Compteur messages/requête | ✅ |
| Buckets ≥ 30 s, plus de saturation p95 | ✅ (vue OTel) |
| Hors périmètre, rien ne coûte | ✅ (test dédié) |
| Décomposition + **phrase attribuable** dans le rapport | ✅ |
| Reste inexpliqué **dit**, jamais absorbé | ✅ |
| Tests scope + rendu, dont « aucune donnée » | ✅ 23 cas |
| Aucune donnée de santé en étiquette | ✅ (test PGSSI-S dédié) |
| **Contre-épreuve au banc (local + distant)** | ⏳ **différée** — exige le banc |

Commits : `b8f340a` (feat), `670cb50` (simplify), `86c03fb` (sonar).

## Merged

- **api-mail** : PR #177 squash-mergée sur `develop` — commit **`4d8846b`** (2026-08-09).
- Branche distante `feat/task-245-enrichment-phase-telemetry` supprimée ; **branche locale conservée**.
- **dtos-mss** : branche `feat/task-245-...` restée vide, aucune PR — non supprimée.
- **CI `develop`** : ✅ verte après merge.
- Attestation humaine `--i-tested` fournie le 2026-08-09.

> ⚠️ Contre-épreuve encore due : la décomposition doit être **lue** sur un tir
> (local **puis** distant, pour ne pas imputer au réseau ce qui appartient au
> traitement). Section « Où part le temps d'un enrichissement » du rapport.
