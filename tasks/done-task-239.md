# todo-task-239.md — L'enrichissement ne détient plus le verrou de session pendant le pipeline CDA : le parcours du médecin n'attend plus derrière son propre traitement

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune (task-238 touche la jambe SMTP, celle-ci la jambe IMAP —
coordination légère au moment des merges, pas de blocage)
**Priorité**: **1** — c'est LE plafond mesuré du palier 200 médecins : tant qu'il
tient, aucune re-certification 200 n'a de sens, et l'US « hydratation fiche
patient » reste indécidable (sa queue à 200 vient de cette contention).

## Objective

Qu'un médecin dont un traitement d'analyse tourne en arrière-plan puisse
continuer à consulter sa boîte : ouvrir l'inbox, lire un message, ouvrir une
fiche patient — **sans attendre que son traitement ait fini**. Aujourd'hui,
l'enrichissement détient le verrou de session IMAP pendant **tout** son
pipeline (téléchargement IMAP, extraction IHE-XDM, parsing CDA, écritures
base), alors que seule la phase de téléchargement a besoin de la session.

**Contraintes absolues** :
- **Aucun changement de contrat** : mêmes routes, mêmes réponses, même
  sémantique d'enrichissement (déduplication, générations UIDVALIDITY,
  complétude des documents produits — le contenu clinique ne disparaît jamais
  en silence, task-227).
- **Le CDA continue de transiter par `interop-cda`** et sa validation — seul le
  *moment où le verrou est tenu* change, jamais le traitement lui-même.
- La **cohérence de session IMAP est préservée** : les opérations réellement
  IMAP (SELECT/FETCH) restent sérialisées sous le verrou comme aujourd'hui.

## La mesure — re-certification K=1 du 2026-08-06 (`report-journey-certif-n200-120344`)

| Signal | Valeur | Lecture |
|---|---|---|
| Détention `imap_session` par `EnrichEmails` | **7,44 s p95**, 12,5 acq/s | le pipeline complet (réseau + parse + base) sous verrou |
| Attente `UpdateFlag` / `GetFolders` derrière | 0,88 s / 0,49 s p95 | le parcours du médecin fait la queue |
| Inbox (étape 2) à 200 médecins | p95 **4 112 ms** (cible 1 000) | ✅ à 50 et 100 — c'est la contention, pas un coût fixe |
| Contenu (`emails/content`) côté serveur | p95 max **10 000 ms** | des lectures à 25 ms p50 coincées derrière un enrich |
| Fiche patient (étape 11) à 200 | p95 4 692 ms (cible 4 000) | ✅ à 50/100 — même cause, US hydratation en attente de ce correctif |

Contexte d'instrument : ces chiffres datent du harnais corrigé (`f209ce8`) —
avant lui, l'enrichissement court-circuitait sur des contenus fantômes et ce
coût était invisible. À 50 et 100 médecins, 10 étapes sur 11 sont vertes ;
à 200, la contention fait tomber les étapes 2, 3 (p95), 6 (préexistant, task-238)
et 11.

## Remèdes demandés

1. **Réduire la portée du verrou au strict IMAP** : sous le verrou, uniquement
   le téléchargement des parties nécessaires (message + pièce jointe) ;
   extraction IHE-XDM, parsing CDA (`interop-cda`), calculs et écritures base
   se font **hors verrou**, sur les octets déjà téléchargés.
2. **Lots courts** : entre deux messages d'un même lot d'enrichissement, le
   verrou est relâché (ou re-acquis par message/sous-lot) pour laisser passer
   les gestes interactifs du médecin — l'esprit des sous-lots de task-228,
   appliqué au verrou et non plus seulement à la phase A.
3. **Instrumenter la preuve** : la table « verrou par opération » du banc doit
   montrer la nouvelle détention d'`EnrichEmails` (attendu : de 7,44 s à
   l'ordre du téléchargement seul, ~1–2 s sous latence mssante), et l'attente
   des opérations interactives (`GetFolders`, `UpdateFlag`, `GetEmailContent`)
   doit chuter en conséquence.

**Hors périmètre (décisions explicites)** : une session IMAP *dédiée* à
l'enrichissement (doublerait les sessions par praticien — le dimensionnement
Dovecot/1000 vient d'être desserré, ne pas le re-serrer sans mesure) ; toute
modification du pipeline CDA lui-même ; l'hydratation de la fiche patient
(US séparée, à re-mesurer après celle-ci).

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] **Zéro changement de contrat** : routes, codes HTTP, corps de réponse et sémantique d'enrichissement inchangés — tests d'intégration existants inchangés
- [ ] Unit tests : le parsing/l'écriture base s'exécutent hors verrou (test d'ordre d'appels sur le scope du verrou — mock : aucune acquisition pendant la phase parse/persist) ; le téléchargement reste sous verrou ; un échec de parse ne laisse jamais le verrou détenu
- [ ] La complétude clinique est préservée sous concurrence : un geste interactif intercalé entre deux messages d'un lot ne fait ni perdre ni dupliquer un document (test d'intégration)
- [ ] Aucune donnée de santé en clair dans les logs (les traces du verrou ne portent ni sujet, ni contenu CDA, ni INS)
- [ ] **Contre-épreuve au banc (bloquante pour le merge, pas pour la PR)** : re-certification K=1, 200 médecins, iso-conditions avec `journey-certif-n200-120344` :
  - détention `EnrichEmails` p95 **≤ 2 s** (référence : 7,44 s)
  - étape 2 (inbox) p95 **≤ 1 000 ms** à 200 médecins (référence : 4 112 ms)
  - étape 3 p95 ≤ 500 ms et `journey_warm_served_from_store` ≥ 95 % (référence : 888 ms / 99,4 %)
  - fiche patient (étape 11) : p95 re-mesuré et consigné — c'est le chiffre qui décide de l'US hydratation
  - 0 régression sur les étapes déjà vertes, erreurs < 0,1 %, vérification par base PASS

## Manual Test Plan

- Monter le banc : skill `loadtest-skill` (profil `https-load-test`)
- Depuis une session, déclencher un enrichissement d'un lot (`POST
  .../emails/enrich/sync` sur 10 UIDs frais) et, **pendant** qu'il tourne,
  enchaîner depuis la même identité : `GET /mail/folders`, lecture d'un contenu
  déjà servi base, `mark read`
- Vérifier : les gestes interactifs répondent en dizaines/centaines de ms
  (aujourd'hui : bloqués jusqu'à ~7 s) ; l'enrichissement aboutit avec le même
  nombre de documents médicaux qu'avant (comparer `hasMedicalDocuments` sur le
  lot)
- Contre-épreuve chiffrée : tir de re-certification K=1 200 médecins (voir DOD)
  et lecture de la table « Verrou de session `imap_session`, par opération »

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — optimisation interne de concurrence
- **Exigences DSR honorées** : non applicable — aucun changement fonctionnel ; la complétude du traitement des documents (CI-SIS) est explicitement préservée par la DOD
- **INS** : non applicable — aucun traitement d'identité modifié ; l'identito-vigilance du rattachement documentaire est inchangée
- **Authentification PS** : inchangée
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable — le CDA transite toujours par `interop-cda` avec la même validation ; seul le moment de détention du verrou change
- **MSSanté** : non applicable — la jambe SMTP n'est pas touchée (task-238) ; les sessions IMAP restent authentifiées à l'identique
- **Tracé PGSSI-S** : inchangé — mêmes évènements de traitement ; les métriques de verrou n'exposent aucune donnée patient
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : inchangé — aucun nouveau traitement de données

## Branches

- `api-mail` (pushed) : `fix/task-239-enrich-lock-scope` —
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-239-enrich-lock-scope
- `dtos-mss` (pushed) : même nom — **auto-incluse**, aucun changement de contrat attendu
  (contrainte absolue de la US) ; si vide, aucune PR, suppression au merge
  (8ᵉ occurrence attendue du défaut de cycle).

Pré-flight vert sur les six repos mesurables. Dépendances : aucune (task-238 mergée le
2026-08-07, jambe SMTP — celle-ci travaille la jambe IMAP, coordination sans blocage).


## Develop log

Commit `827e0ed` sur `fix/task-239-enrich-lock-scope` (api-mail seul — dtos-mss intouché,
aucun changement de contrat). Diff : 3 fichiers, 460 insertions / 64 suppressions.

### État des lieux — deux remèdes sur trois étaient déjà en place

La US demandait « verrou au strict IMAP » (remède 1) et « lots courts » (remède 2). L'analyse
du code a montré que **le parse CDA et les écritures base tournaient déjà hors verrou**
(Phase B, task-079) et que **le verrou était déjà pris par sous-lot** (task-228, 15 messages).
Le vrai coupable des 7,44 s p95 : la fenêtre de sous-lot couvre le fetch séquentiel des corps
et pièces jointes de 15 messages — ~45 allers-retours sous latence mssante. `ExtractIheXdmZipsAsync`
sous verrou ne fait que télécharger les octets du zip (réseau, légitime) ; le parse
(`ProcessIheXdmZips`) vit dans `BuildMailDtoAsync`, Phase B.

### Le remède livré — fenêtres de verrou par message

`FetchEnrichmentChunkAsync` restructuré : une fenêtre courte « résumés » par sous-lot
(connexion + SELECT + FETCH des enveloppes — seule fenêtre à payer `ConnectInternalAsync`,
qui relit les réglages en base), puis **une fenêtre par message** (`FetchSingleMailWindowAsync`)
pour ses corps et PJ. Chaque intervalle laisse passer un geste du médecin. Détails :

- **Zéro coût ajouté sur le chemin nominal** : les fenêtres message réutilisent le client et
  le dossier résolus par la fenêtre résumés — pas de reconnexion, pas de lecture base, pas de
  re-SELECT. Le dossier n'est rouvert (1 aller-retour) que si un geste intercalé l'a
  réellement désélectionné.
- **Le travail réseau payé survit aux coupures de milieu de sous-lot** : le contrat de retour
  (`EnrichmentChunkFetch`) porte les messages lus AVEC l'indication d'abandon — avant, un
  `null` les jetait. Les messages lus partent en persistance, les UIDs restants redeviennent
  pending.
- Étiquette de verrou par message `EnrichEmails:{folder}:{uid}` — même famille `EnrichEmails`
  dans la table « verrou par opération » du banc (troncature au premier `:`), la preuve
  chiffrée du remède 3 est donc mesurable sans changement d'instrumentation. Aucune donnée de
  santé dans les libellés (dossier, UID, hash).

### Tests

- **6 tests mis à jour au nouveau contrat** (comptage des fenêtres : 3 UIDs ⇒ 1+3 ; chunk 2,
  5 UIDs ⇒ 3+5=8 ; libérations avant persistance ×2). **Preuve par mutation : les 6 étaient
  ROUGES sur le code par sous-lot** — qui est exactement la mutation « lot redevenu
  monolithique ».
- **4 tests neufs unitaires** : dossier mort en milieu de sous-lot ⇒ le message déjà lu est
  persisté, ni perdu ni fantôme ; dossier désélectionné par un geste ⇒ rouvert à chaque
  fenêtre, lot intègre ; parse/persist jamais sous verrou (traçage détention via substitut,
  DOD) ; échec de parse ⇒ verrou ni détenu ni fuité (locks == unlocks, persist lock rendu).
- **1 test d'intégration neuf** (`EnrichmentLockInterleavingTests`) : **vrai**
  `MailClientSessionManager` (vrai sémaphore, vraies portées), transport IMAP simulé — un
  geste interactif arrive PENDANT la fenêtre du 1er message (bloqué, asserté), passe ENTRE
  les deux fenêtres (asserté, timeout = régression), et le lot est persisté exactement une
  fois par message (ni perte ni doublon — l'item DOD).

### Validation

Build 0 erreur / 0 avertissement · domain 136/136 · infrastructure 419/419 ·
application **2041/2041** · api 650/650 · integration **370/370** (16 ignorés).
S103 vérifié (aucune ligne > 150). Conventions csharp.md relues et appliquées.

### 🚧 Contre-épreuve au banc — bloquante pour le merge, non faite ici

Le DOD l'exige : re-certification K=1 n200 iso-conditions avec `journey-certif-n200-120344` —
détention `EnrichEmails` p95 ≤ 2 s (réf. 7,44 s), inbox p95 ≤ 1 000 ms à 200 (réf. 4 112),
étape 3 p95 ≤ 500 ms et warm ≥ 95 %, fiche patient re-mesurée (décide l'US hydratation),
0 régression sur les étapes vertes. Le banc n'est pas monté dans ce cycle.


## Simplify log

**Skip propre.** Le diff (3 fichiers, 460 insertions) est déjà au bon niveau : fenêtre par
message extraite (`FetchSingleMailWindowAsync`), sorties lisibles par fabriques
`Continue`/`Abort`, aucun aller-retour ajouté au chemin nominal. Candidats examinés et non
retenus : mapper le retour sur `Ardalis.Result` (l'abandon doit voyager AVEC les messages
lus — un `Result.Error` ne porte pas de valeur, le record dédié est plus juste) ; factoriser
l'idiome `!IsOpen && !TryOpenFolderAsync` (idiome préexistant du fichier, 4 autres sites hors
diff — hors périmètre d'une passe task-scoped).


## Sonar log

Scan direct sur la branche `fix/task-239-enrich-lock-scope` (scanner local, EXECUTION SUCCESS,
build Release + 5 suites avec couverture OpenCover — toutes vertes).

### KPIs qualité (baseline → final)

| Métrique | Baseline (task-238) | Final (task-239) |
|---|---|---|
| Quality Gate (new code) | **ERROR** | **ERROR** |
| `new_violations` | 28 | **32** |
| `new_coverage` | 86.9 % | **87.5 % — OK** ✅ |
| `new_security_hotspots_reviewed` | 71.4 % | 71.4 % (2 restants) |
| `new_duplicated_lines_density` | 0.08 % — OK | 0.07 % — OK |

### Attribution

- **Zéro** des 32 violations dans un fichier touché par task-239 (`ImapService.cs`,
  `ImapServiceTests.cs`, `EnrichmentLockInterleavingTests.cs` — vérifié fichier par fichier
  via l'API issues). La passe n'a rien à corriger sur le code de la task.
- 26/32 dans l'outillage de banc `tests/loadtest-k6/` (tasks 174/195, hérité) : `report.py`
  (15, dont 8 S3776 et le bug S1244), `journey.js` (7), `journey-model.js` (4). Les 2 hotspots
  non révisés = `Math.random()` de `journey.js` — **10ᵉ signalement**.
- **6/32 dans des fichiers de task-238** (mergée le 2026-08-07 au matin), visibles post-merge
  dans la new-code period `PREVIOUS_VERSION` : `SmtpConnectionFactory.cs` S103 (ligne
  152 car.), `MailClientSession.cs` S3776 (19), `SmtpSessionKeepAliveTests.cs` CA1816
  (`Dispose` sans `GC.SuppressFinalize`), `MailServerDiscovery.cs` ×2. Le scan de task-238
  n'en signalait aucun dans ses fichiers — écart vraisemblablement lié aux retouches
  tardives de son cycle (Dispose idempotent). **Hors périmètre task-239** (règle 6, scopes
  isolés) — matière à une passe d'entretien.

### Décision

Acceptation best-effort, aucune itération de fix — rien à corriger dans le périmètre de la
task ; les findings restants appartiennent aux tasks d'outillage (174/195) et à task-238
(déjà mergée). `new_coverage` en hausse (87.5 %), les deux causes du QG ERROR restent
entièrement héritées (hotspots k6 jamais révisés + violations d'outillage/task-238).


## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/170 —
  label `awaiting-human-merge`. Run CI PR déclenché normalement (`build` pending à
  l'ouverture — Actions rétabli depuis le 2026-08-07 au matin).
- `dtos-mss` : branche auto-incluse **vide** (0 commit), aucune PR — **8ᵉ occurrence** du
  défaut de cycle « branche auto-incluse jamais utilisée ».

## Code Review Summary

**APPROVED — 0 blocage** (3 fichiers revus, diff 460 insertions / 64 suppressions).

- Chaque sortie de fenêtre passe par la disposition du scope (`await using`) — verrou jamais
  fuité, y compris sur exception non-IMAP (catch générique → `Abort(fetched)`, travail
  réseau préservé).
- Ownership `FetchedMail` : un seul propriétaire à tout instant — pas de double-dispose
  (OCE : le chunk libère les siens puis rethrow ; l'appelant libère l'accumulé en `finally`).
- Équité : waiters `SemaphoreSlim` FIFO — le geste interactif en attente passe devant la
  ré-acquisition immédiate de la boucle d'enrichissement (prouvé par le test d'intégration
  au vrai session manager).
- Risque UIDVALIDITY entre fenêtres : même enveloppe que task-228 (générations confrontées à
  la persistance) — la granularité change, l'exposition non.
- Aucune donnée de santé dans les libellés de verrou (dossier, UID, hash).
- ⚠️ Trade-off documenté (non bloquant) : un geste qui change de dossier au milieu d'un lot
  force un re-SELECT par fenêtre message suivante (1 aller-retour chacune) — payé uniquement
  sous entrelacement réel, c'est le prix du partage de connexion.

**Validation finale /review** : build 0 erreur / 0 avertissement ; suites 136 / 419 / 2041 /
650 / 370 (16 ignorés) — tout vert sur bin normal.
**DOD** : tous les items vérifiés ; item « contre-épreuve au banc » = **bloquant pour le
MERGE, non fait** (banc non monté) — consigné dans la PR.
