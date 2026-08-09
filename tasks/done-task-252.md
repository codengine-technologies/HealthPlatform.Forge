# todo-task-252.md — Télécharger une pièce jointe passe de 1 à 4,8 secondes entre 200 et 500 praticiens

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-244** (chauffe) — la mesure de confirmation exige un tir
500 valide. La **première moitié** de cette US (établir la cause) n'attend rien.
**Priorité**: **2** — c'est le goulot **G2** du tir 500 : une étape verte à 100 et
200 qui sort franchement de la grille à 500, avec des abandons.

## Objective

Établir **pourquoi** le téléchargement d'une pièce jointe s'effondre entre 200 et
500 praticiens — puis seulement décider du remède.

⚠️ **US en deux temps, et l'ordre n'est pas négociable** : mesurer, puis corriger.
Cette EPIC a annulé une US applicative écrite sur une cause plausible et fausse
(task-222).

## Ce qui est établi

Tir `journey-remote-n500` du 2026-08-09, étape « Télécharger une PJ (~124 Ko) » :

| Palier | p50 | p95 (cible 2 000 ms) | Verdict |
|---|---|---|---|
| 100 médecins | — | dans la grille | ✅ |
| 200 médecins | — | dans la grille | ✅ |
| **500 médecins** | **573 ms** | **4 771 ms** | ❌ + **16 abandons** (HTTP 0) |

Le smoke comparatif local/cluster l'avait signalé à **+45 %** sur 6 échantillons
seulement — donc sans valeur probante à ce stade ; le tir le confirme sur **5 162**.

**Ce qui est déjà écarté** : ce n'est pas un plafond matériel. Aucune ressource
n'est épinglée sur ce tir (CPU maximal **8,3 % de 24 cœurs**, file ThreadPool
calme, RSS plate). Le plafond est dans une **dépendance sérialisée**.

**Une réserve de méthode à porter dans l'analyse** : ce tir tournait sur une base
quasi vide (chauffe échouée), donc le chemin base est sous-sollicité. Cela **ne
disqualifie pas** ce constat — le téléchargement d'une PJ est un chemin **IMAP**,
peu dépendant du contenu de la base — mais il faudra le reconfirmer sur un tir à
chauffe réussie.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que c'est le NFS du cluster.** C'est le candidat commode. Le
  smoke a mesuré la lecture froide IMAP à **+6 %** seulement entre local et
  cluster : le stockage distant ne dégradait pas les lectures à faible charge. À
  500, c'est peut-être différent — mais il faut le **mesurer**, pas le supposer.
- **Ne pas présumer que c'est le verrou de session IMAP.** C'est le candidat
  historique de cette EPIC, et il a déjà été écarté une fois sur un autre chemin.
- **Ne pas présumer que c'est la taille.** 124 Ko à 94 ms de latence injectée ne
  font pas 4,8 s à eux seuls : il y a de l'attente quelque part, à localiser.

## Definition of Done

- [ ] La cause est **établie** par la télémétrie, pas supposée : décomposition
      d'une requête représentative (contexte, acquisition de session, fetch
      `BODY[part]`, streaming vers le client), avec les requêtes qui l'établissent
- [ ] Il est dit explicitement si la cause est **côté serveur mail** (Dovecot/NFS)
      ou **côté api-mail** — les deux remèdes n'ont rien à voir
- [ ] Les 16 abandons sont expliqués : côté client (délai) ou côté serveur
- [ ] Si un correctif est livré : A/B iso-conditions, un seul facteur, et l'étape
      rentre dans la grille au palier 500
- [ ] Si aucun correctif n'est livré : le **dire**, écrire pourquoi, et poser le
      seuil qui rouvrirait le sujet
- [ ] Ce que la télémétrie n'a **pas** pu dire est écrit — c'est le backlog
      d'instrumentation de la US suivante

## Manual Test Plan

- Monter le banc en mode distant, tir `journey` avec paliers 200 puis 500
- Pendant le palier 500, ouvrir un message et télécharger sa pièce jointe depuis
  l'application : le fichier doit arriver **complet et intègre** (l'archive
  IHE_XDM doit s'ouvrir), quelle que soit la latence
- Relever en parallèle le CPU des pods du cluster (`kubectl top pods`) pour
  distinguer un plafond serveur mail d'un plafond api-mail

Données de test synthétiques uniquement.

## Branches

- `api-mail` (pushed) : `feat/task-252-attachment-download-phases`
- `dtos-mss` (pushed, auto-inclus) : même nom — aucun changement de contrat

## Develop log

- Repos touchés : `api-mail`. `dtos-mss` : branche vide.
- Commit : `4370284` — `feat(telemetry): decomposer le temps d'un telechargement de piece jointe en phases`.

### ⚠️ Ce que cette US NE fait pas : établir la cause

**Le DOD n'est pas rempli, et c'est le résultat honnête à ce stade.** Deux
blocages indépendants, dont un seul était levable ici :

1. **La télémétrie qui permettrait de répondre n'existait pas.** Tout le chemin
   de téléchargement ne portait **qu'une seule** activité
   (`StartImapActivity("GetAttachmentStream")`) couvrant la méthode entière.
   Aucune requête, sur aucun tir passé ou futur, n'aurait pu répartir les
   4 771 ms entre le court-circuit base, l'acquisition de session, le fetch
   `BODY[part]` et la sortie vers le client. **Ce blocage-là est levé** — c'est
   le livrable de cette étape.
2. **Le tir qui produirait la mesure n'est pas exécutable ici.** Le Manual Test
   Plan demande le banc **en mode distant** (paliers 200 puis 500) et
   `kubectl top pods`. L'accès au cluster n'est pas disponible dans cette
   session (commande `kubectl` refusée), et le skill du banc classe le
   déploiement distant en étape **humaine** (« Déploiement (humain — accès
   cluster) »). Un tir 500 **local** ne vaudrait rien : le skill documente que
   « tout chiffre > 500 mesuré banc local est un artefact connu » (Dovecot vole
   2,6 cœurs au SUT).

**L'ordre imposé par le task file est respecté : mesurer, puis corriger.**
Aucun correctif n'est livré, et c'est délibéré — désigner le verrou de session
(candidat historique, déjà écarté une fois sur un autre chemin) ou le NFS du
cluster (candidat commode, mesuré à +6 % seulement à faible charge) sans mesure
serait exactement la faute qui a coûté l'annulation de task-222.

### Ce qui est livré : l'instrument qui rendra la question décidable

Quatre phases, choisies parce que **chacune désigne un remède différent** —
c'est le critère qui a présidé au découpage, pas la commodité d'implémentation :

| Phase | Ce qu'elle couvre | Ce que sa domination signifierait |
|---|---|---|
| `db_lookup` | le court-circuit base (PJ déjà en cache ?) | le sujet est **la base**, pas du tout le serveur mail |
| `session_acquire` | verrou de session + connexion IMAP + ouverture du dossier | la **voie d'accès à la session** — le candidat historique |
| `imap_fetch` | BODYSTRUCTURE puis `BODY[part]` | la cause est **côté serveur mail** (Dovecot/NFS) et **aucun remède applicatif ne la touchera** |
| `stream` | l'écriture de la réponse au client | ni la base ni le serveur mail : **la sortie** |
| `assemble` | le reste, par différence | ce que la prochaine US découperait |

C'est **exactement** la distinction que le DOD demande de trancher (« il est dit
explicitement si la cause est côté serveur mail ou côté api-mail ») : elle se
lira désormais d'une requête.

### Le choix de conception qui méritait d'être discuté

**`stream` est mesurée par `Response.OnCompleted`, pas par un flux enveloppé.**

L'action rend un `FileStreamResult` : l'écriture au client a lieu **après** son
retour. Un chronomètre refermé en fin d'action aurait mesuré tout **sauf** la
sortie — c'est-à-dire tout sauf l'un des quatre suspects.

Envelopper le flux aurait marché aussi. C'est écarté : la pièce jointe **est**
le document clinique, et le task file pose l'intégrité de l'archive en critère
**bloquant** — « une troncature silencieuse serait une perte de donnée de santé,
et prime sur toute considération de performance ». Un rappel de fin de réponse
ne touche pas un octet. Épinglé par un test :
`DownloadAttachment_MeasurementPutsNothingOnTheByteStream` vérifie que le flux
rendu au framework est **exactement l'instance** produite par le service — si
quelqu'un ajoute un jour un décorateur de mesure, il tombe là.

### Tests (7 + 1)

- Attribution de chaque phase à sa propre étiquette, enveloppe publiée **une**
  fois et **séparément** (la sommer avec les phases doublerait le total).
- **Témoin négatif** « absence ≠ zéro » : les phases non parcourues sont
  publiées **à zéro**, jamais omises. Sans lui, un instrument publiant des
  constantes passerait le premier test.
- Rien hors périmètre : les mêmes services servent d'autres chemins.
- Non-ré-entrance (le temps d'une opération interne est déjà compté au-dessus).
- Publication **malgré une exception** — un téléchargement qui échoue est
  précisément l'un des cas qu'on veut lire.
- `assemble` borné à zéro, jamais négatif.
- **PGSSI-S** : unique étiquette `phase`, valeurs dans un ensemble fini de
  littéraux ; l'enveloppe ne porte **aucune** étiquette. Aucun nom de fichier
  (la fuite qu'a évitée task-213), aucun UID, aucun INS.

### Validation

- Build : **0 erreur, 0 avertissement**.
- Tests : domain 136 · infrastructure 436 · api **660** · integration 384 ·
  application **2 108** → **3 724 verts**.
  Un échec, **flaky pré-existant documenté** :
  `MailExportServiceTests.BuildPdfPrintIntentEmbedsPrintWording` — **vert en
  isolation (22/22)**, et sans rapport avec ce diff (export PDF ≠ télémétrie de
  téléchargement).

### Ce que la télémétrie ne dira toujours PAS (DOD, backlog de la US suivante)

1. **La répartition à l'intérieur de `session_acquire`** entre *attendre le
   verrou* et *ouvrir/authentifier la connexion*. Les deux sont comptés ensemble
   parce qu'ils désignent le même remède ; si cette phase domine, c'est **elle**
   que la US suivante découpe.
2. **Le débit d'octets de la sortie.** `stream` donne une durée, pas des
   octets/s : une sortie lente et une sortie volumineuse s'y lisent pareil.
3. **Le côté serveur.** Aucune métrique d'api-mail ne dira si Dovecot ou le NFS
   sont le mur — d'où `kubectl top pods` dans le Manual Test Plan, qui reste un
   geste humain.
4. **Les 16 abandons ne sont pas expliqués** (DOD non rempli) : décider s'ils
   sont client (délai k6) ou serveur exige de les observer sur un tir. ⚠️ Point
   d'attention pour ce tir : un client qui abandonne **peut** ne jamais faire
   aboutir `Response.OnCompleted`, donc les abandons risquent d'être **absents**
   de l'histogramme plutôt que d'y figurer comme longs. À vérifier au premier
   tir — et si c'est le cas, c'est un compteur d'abandons qu'il faut ajouter,
   pas une durée.

### Le seuil qui rouvre le sujet

L'étape rentre dans la grille si son **p95 au palier 500 repasse sous
2 000 ms**. Tant qu'il reste au-dessus, le sujet est ouvert. Premier geste au
prochain tir 500 à chauffe réussie :

```
sum by (phase) (
  rate(mssante_attachment_download_phase_duration_seconds_sum[2m])
) / on() group_left
  rate(mssante_attachment_download_duration_seconds_count[2m])
```

⚠️ Relever la requête **dans** la fenêtre du tir : une `rate` évaluée après coup
rend une série vide (piège documenté).
- Next step : `/forge-simplify 252`

## Simplify log

- **Skip clean.** Le code livré **réutilise** délibérément le patron de
  task-245 (`EnrichmentOperationScope`) : même mécanique `AsyncLocal`, même
  non-ré-entrance, même « rien hors périmètre », même harnais de capture côté
  tests. C'est la forme la plus simple **et** la plus cohérente avec l'existant ;
  factoriser les deux périmètres en une base commune serait une abstraction
  prématurée sur deux occurrences aux cycles de vie différents (l'un se referme
  sur un `using`, l'autre sur la fin de réponse).
- Next step : `/sonar 252`

## Sonar log

Analyse complète relancée (du C# est modifié, dont **deux fichiers lourds** —
`ImapService.cs` et `MailController.cs`) : build Release + 5 projets de tests
avec couverture OpenCover + scanner. `EXECUTION SUCCESS`.

### KPIs qualité

| Métrique | Valeur |
|---|---|
| Quality Gate (new code) | **ERROR** — non imputable, voir ci-dessous |
| Couverture new code | **87,9 %** (seuil 80 ✅) — inchangée malgré 6 fichiers touchés |
| Duplication (new code) | 0,06 % (seuil 3 ✅) |
| Ratings (fiabilité / sécurité / maintenabilité) | C / A / A |

### Lecture — dette introduite par task-252 : **zéro**

`new_violations = 56`, dont **0 dans un fichier de cette task** (les 6 fichiers
du diff vérifiés d'un coup, y compris les deux gros fichiers touchés). Ce sont
les **mêmes 56** qu'à task-249 quelques minutes plus tôt : `report.py` (20),
`journey-model.js` (10), `journey.js` (7), tests d'embedding (9), divers (10) —
du code de tasks **déjà mergées** encore dans la new-code period.

Point notable : ajouter ~200 lignes de production **n'a pas bougé la couverture
new code** (87,9 % avant comme après). L'instrument arrive couvert.
- Next step : `/lint-angular 252` → skip → `/review 252`

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — performance
- **Exigences DSR honorées** : aucune exigence nouvelle ; ⚠️ la pièce jointe **est**
  le document clinique — une troncature silencieuse serait une perte de donnée de
  santé, et prime sur toute considération de performance
- **INS** : l'archive IHE_XDM porte des CDA avec INS — aucun contenu ni nom de
  fichier patient dans les journaux ou les étiquettes de métrique
- **Interop CI-SIS** : volet transport MSSanté / IHE-XDM — l'intégrité de l'archive
  est un critère **bloquant** de cette US
- **Habilitations** : un praticien ne doit pouvoir télécharger que les pièces de
  **ses** messages — à re-vérifier si le chemin de streaming est modifié
- **Authentification PS / Consentement** : inchangés
- **Tracé PGSSI-S** : inchangé
- **Hébergement HDS** : le verdict devra être transposable à la cible
- **AIPD / impact RGPD** : inchangé

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/183 — label `awaiting-human-merge`
- `dtos-mss` : aucune PR — 0 commit (branche auto-incluse vide, 19e occurrence)
- Staging du run : `forge/staging-task-249-252-20260809` — task-249 **et** task-252 agrégées

## Code Review Summary

**Verdict : APPROVED** — 6 fichiers, 0 blocage, 1 suggestion non bloquante.

- `AttachmentDownloadScope.cs` — ✅ calque assumé de `EnrichmentOperationScope`
  (task-245) : même `AsyncLocal`, même non-ré-entrance, même « rien hors
  périmètre ». Une divergence, justifiée et documentée : la fermeture est
  **explicite** et non un `using`, parce que la phase de sortie se paie après le
  retour de l'action.
- `MailProcessingMetrics.cs` — ✅ instruments séparés (enveloppe / phases), même
  raison qu'à task-245 : un `sum by (phase)` compterait sinon le total en plus de
  ses parties. Étiquette unique et littérale.
- `ImapService.cs` — ✅ trois chronomètres, et les chemins de sortie anticipée
  (connexion échouée, partie introuvable) publient **aussi** leur phase — sans
  quoi les échecs disparaîtraient de la mesure, alors que ce sont eux qu'on veut
  lire.
- `MailController.cs` — ✅ le `try/finally` garantit qu'aucun chemin ne perd la
  mesure : soit le périmètre est transmis au rappel de fin de réponse, soit il
  est publié sur place. ⚠️ **Suggestion non bloquante** consignée dans la PR :
  un client qui abandonne peut ne jamais faire aboutir `Response.OnCompleted` —
  à vérifier au premier tir, et si confirmé c'est un **compteur d'abandons**
  qu'il faudra, pas une durée.
- **Sécurité / PGSSI-S** : aucune donnée de santé en étiquette (test dédié) ; la
  mesure ne met **rien** sur le chemin d'octets du document clinique (test
  dédié). Habilitations inchangées — le chemin de streaming n'est pas modifié.
- **Performance** : l'instrument ne fait qu'ajouter des `Stopwatch.GetTimestamp`
  et des `Interlocked.Add` ; aucune allocation par phase, aucun appel réseau.
