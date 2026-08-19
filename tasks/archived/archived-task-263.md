# todo-task-263.md — Le harnais postule que les UID commencent à 1 : dès qu'une boîte a vécu, il rend des verdicts verts sans rien mesurer

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune.
**Priorité**: **2** — ce défaut a **invalidé deux campagnes distantes**. Il ne
casse pas le banc : il le fait mentir, ce qui est pire.

## Objective

Qu'une campagne puisse s'exécuter sur des boîtes dont les UID ne commencent pas à
1, ou qu'elle **refuse de démarrer** — mais qu'elle ne rende jamais un verdict
sur des messages inexistants.

## Ce qui est établi

`lib/uid-bands.js` calcule ses bandes par `start = 1 + batchIndex * enrichBatch`,
et `journeyReserves` code en dur `start: 1`. Les deux postulent qu'une boîte
commence à l'UID 1.

**Ce postulat n'est vrai que sur un maildir vierge.** Les UID IMAP ne sont
**jamais réutilisés** : purger une boîte par IMAP (`doveadm expunge`) supprime
les messages mais laisse le compteur avancer. Un re-seed repart donc au-delà.

**Mesuré le 2026-08-14** : les 500 boîtes du banc distant portaient les UID
**201 à 447** après une purge par IMAP suivie d'un re-seed. Aucun message n'avait
d'UID entre 1 et 10.

**Ce que le banc rendait dans cet état** — vérifié à la main avant de lancer la
campagne :

| Geste | Réponse | Réalité |
|---|---|---|
| `enrich/sync` sur les UID 1–3 | **HTTP 200 en 1,04 s** | 0 mail, 0 contenu, 0 document en base |
| Lecture des UID 1–5 | HTTP 200 | rien à lire, repli sur IMAP |

**Aucune erreur, aucun seuil franchi, aucun signal.** Un escalier complet aurait
rendu des verdicts **verts et flatteurs**. C'est mot pour mot ce qui s'est
produit lors de la première tentative distante à 500 : *« 8/11 vertes parce que
la base est vide »*.

**Le contournement existe mais ne corrige rien** : le Job
`maildir-purge-job.yaml` efface les répertoires de boîte et fait repartir les UID
de 1. Il remet le compteur à zéro ; il n'empêche pas le défaut de revenir à la
purge suivante.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que la purge suffit.** Elle a été faite le 2026-08-14, et le
  défaut reviendra à la prochaine boîte qui aura vécu.
- **Ne pas présumer qu'un décalage fixe suffit.** Deux boîtes peuvent avoir des
  UID de départ différents — trois boîtes du banc en portaient déjà, du fait d'un
  calibrage. Un décalage global les traiterait toutes comme la plus basse.
- **Ne pas se contenter d'un paramètre.** Un `UID_BASE` mal réglé reproduit le
  défaut en silence. **Le refus de démarrer est au moins aussi important que le
  décalage.**

## Ce que la US doit livrer

Deux choses, et la seconde est la plus importante :

1. **Un décalage d'UID**, de sorte que les bandes visent les messages qui
   existent réellement.
2. **Un contrôle au démarrage** : le `setup()` vérifie que la bande visée
   **existe** dans la boîte, et **refuse le tir** avec un message qui nomme la
   cause et le geste — comme le fait déjà le contrôle de budget du parcours, qui
   a refusé une campagne mal dimensionnée le 2026-08-14 **avant** de brûler deux
   heures de banc. C'est le modèle à suivre.

## Definition of Done

- [ ] Build passe, auto-tests du harnais verts (`selftest.sh`) — **y compris les
      tests JS**, ce qui suppose Node disponible ; un SKIP n'est pas un succès
- [ ] Les bandes d'UID (`uid-bands.js` **et** `journey-model.js`) partent d'une
      base **paramétrable**, défaut inchangé à 1
- [ ] Le `setup()` **refuse le tir** quand la bande visée n'existe pas dans les
      boîtes, avec un message qui **nomme la cause et le geste** — sur le modèle
      du contrôle de budget
- [ ] Le refus est **éprouvé** : un test le déclenche, et le message est vérifié
- [ ] Le contrôle porte sur **plusieurs boîtes**, pas une seule — des boîtes
      peuvent différer entre elles
- [ ] Le skill `loadtest-skill` documente le contrôle et le geste de purge
      (`maildir-purge-job.yaml`), en disant **pourquoi `kubectl exec rm -rf`
      échoue** (répertoires `drwx------ 1000:1000`, `root_squash` NFS)
- [ ] **Contre-épreuve** : un tir court sur des boîtes à UID décalés rend des
      chiffres **non nuls** et cohérents, là où il rendait des verdicts verts
      sans travail

## Manual Test Plan

- Sur le banc distant, relever la base d'UID d'une boîte :
  `python` + `imaplib`, `FETCH 1 (UID)` — ou `doveadm`
- Lancer un tir court **sans** décalage sur des boîtes décalées : il doit
  **refuser de démarrer** et nommer la cause
- Relancer **avec** le décalage : le tir démarre, et le nombre de messages
  enrichis doit **égaler** le nombre soumis
- Contrôle de non-régression : sur un maildir vierge (UID à partir de 1), le
  comportement par défaut est **inchangé**

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — outillage de banc
- **Exigences DSR honorées** : aucune — aucun changement fonctionnel
- **INS** : sans objet — outillage de test, données 100 % synthétiques
- **Interop CI-SIS** : sans objet
- **Habilitations** : sans objet
- **Authentification PS / Consentement** : inchangés
- **Tracé PGSSI-S** : inchangé
- **Hébergement HDS** : sans objet — le harnais ne tourne jamais en production
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : feat/task-263-uid-base-refus
- `dtos-mss` (pushed, auto-inclus) : feat/task-263-uid-base-refus — aucune modification attendue

## Develop log (2026-08-15)

**Prérequis DOD levé d'abord** : Node absent du poste (le selftest JS skippait,
et « un SKIP n'est pas un succès ») → installé `OpenJS.NodeJS.LTS` v24.19.0
(winget, scope user), comme Python l'avait été le 2026-07-27.

**Livré** (`286b2ae`) :
- `UID_BASE` (défaut 1, comportement historique intact) — `uid-bands.js` passe
  par un cœur pur node-testable (`uid-bands-core.js`), `journeyReserves` gagne
  un 4ᵉ paramètre ; réserves toujours disjointes sous décalage (testé).
- **Refus de démarrage** — `uid-guard.js` (jugement pur, testé) +
  `uid-probe.js` (sonde k6) : 3 boîtes sondées (première/milieu/dernière) via
  `GET /folders/{f}`, refus nommant boîte + cause + geste ; une sonde muette
  n'est pas un laissez-passer. Branché dans `bootstrap()` (enrich/read/mixed)
  ET dans le `setup()` de journey.
- Doc skill : contrôle documenté, purge = Job `maildir-purge-job.yaml`, et
  pourquoi `kubectl exec rm -rf` échoue (répertoires 1000:1000 + root_squash).

**Tests** : 16 nouveaux cas `node --test`, messages de refus vérifiés
(cause + geste + valeur UID_BASE à poser + boîte divergente seule nommée).
Mutation éprouvée : neutraliser le refus minUid → 2 rouges. `selftest.sh`
intégralement vert : **88 JS + 287 Python, zéro SKIP**.

**Contre-épreuve (DOD) — banc local, mécanisme identique au distant** :
1. Seed 3×10 (UID 1–10) → `doveadm expunge` → re-seed 10 → boîtes à **UID
   11–20, uidnext=21** : l'état exact du 2026-08-14 en miniature.
2. **Sans décalage** : le tir `enrich` **refuse de démarrer** — « les UID de
   loadtest-1@… commencent à 11 alors que la bande visée commence à 1 … Geste :
   poser UID_BASE=11, ou … maildir-purge-job.yaml ». Avant task-263, cette
   configuration rendait HTTP 200 verts sans rien mesurer.
3. **Avec `UID_BASE=11`** : contrôle passe (bande 11..20 présente, 3 boîtes),
   bandes enrich=11..15 / read=16..20, **3/3 enrich HTTP 200, 3/3 « ran the
   CDA pipeline (not short-circuited) », `enrich_short_circuited count==0`** ;
   vérifié côté données : UID 11–13 portent `hasMedicalDocuments=true`.
4. Non-régression maildir vierge : test unitaire « défaut inchangé » (tout
   part de 1) + adaptateur CFG sans changement d'API.

Banc local éteint après la contre-épreuve.

## Simplify log (2026-08-15)

Skip propre — la passe qualité est déjà dans la conception : séparation cœur
pur / adaptateur CFG (le pattern vu-sizing/journey-model du harnais), jugement
pur / sonde k6. Aucun axe actionnable. dtos-mss non touché.

## Sonar log (2026-08-15)

Skip propre — aucun fichier C# modifié (diff 100 % harnais k6 : JS/MJS sous
`tests/loadtest-k6/`, hors périmètre de l'analyse dotnet-sonarscanner). KPIs
inchangés par construction ; Quality Gate develop : OK (relevé task-262).

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/193 — label `awaiting-human-merge`
- `dtos-mss` : aucune modification, pas de PR
- Staging : `forge/staging-task-260-264-20260814` (task-263 agrégée)

## Code Review Summary

APPROVED — 0 blocage. Jugement pur / sonde séparés, contrat task-174 re-prouvé
sous décalage, refus éprouvé par test (message vérifié) ET en live (contre-
épreuve banc local : refus sans décalage, 3/3 travail réel avec UID_BASE=11).
selftest 88 JS + 287 Python, zéro SKIP. Sonar : skip propre (aucun C#).

## Merged

**Date** : 2026-08-19 06:28 UTC — `/merge task-263 --i-tested` (HAG, règle 10 :
l'humain a testé et attesté avant merge).

| Repo | PR | Commit squash sur `develop` |
|---|---|---|
| `api-mail` | [#193](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/193) | `2589ada` |
| `dtos-mss` | aucune PR — branche auto-incluse sans commit | — |

- Six garde-fous passés avant merge : `--i-tested` présent, label
  `awaiting-human-merge`, `reviewDecision` vide (aucun `CHANGES_REQUESTED`),
  CI PR verte (`build` 1m47s, `publish` skipped, run
  [31849827996](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/31849827996)),
  `mergeable = MERGEABLE / CLEAN`, arbres propres sur `api-mail` et `dtos-mss`
  (tous deux déjà sur `develop`).
- Contenu entré sur `develop` : 12 fichiers, +511/−69 — le cœur pur
  `uid-bands-core.js` et son test, le refus `uid-guard.js` + `uid-guard.test.mjs`,
  la sonde `uid-probe.js`, et le branchement dans `bootstrap.js` / `journey.js`.
- Refs **distantes** `feat/task-263-uid-base-refus` supprimées sur `api-mail` et
  `dtos-mss` (jamais `--delete-branch`). La branche `dtos-mss` pointait sur
  `3a54260`, tête de son `develop` — zéro commit, conforme au « aucune
  modification attendue » du task file. Aucune branche locale n'existait sur
  les deux repos — rien à conserver.
- `develop` synchronisé sur `api-mail` (fast-forward) ; `dtos-mss` déjà à jour.
- CI `develop` api-mail : ✅ **verte** — run
  [32223553314](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/32223553314)
  (`completed / success`, tête `2589ada`), conclusion atteinte dans les 2 min de
  la règle 5.
- Branche staging `forge/staging-task-260-264-20260814` **conservée** : task-264
  du même run est encore en `done-*`. Présente sur `api-mail` uniquement (aucun
  autre repo pushable n'en porte).
- **Ce que ce merge change pour le banc** : les verdicts verts sans travail
  mesuré ne sont plus possibles en silence — une bande d'UID absente arrête le
  tir en nommant la boîte, la cause et le geste (`UID_BASE=N`, ou
  `maildir-purge-job.yaml`). Le décalage seul aurait laissé un `UID_BASE` mal
  réglé reproduire le défaut ; c'est le refus qui ferme la porte.
