# todo-task-259.md — `RemoveRange` sur une collection de navigation la modifie pendant qu'il l'énumère : l'enrichissement de contact échoue sous concurrence

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune. **task-250** a travaillé le même bloc (traduction du
conflit de concurrence en `ConflictException` et rejeu) ; ce défaut-ci est
**distinct** : il se produit **avant** `SaveChangesAsync`, donc avant la
frontière que task-250 a posée, et le rejeu ne le rattrape pas.
**Priorité**: **3** — sans effet sur le débit ni sur la lecture du médecin, mais
c'est une **perte silencieuse d'enrichissement de contact** : l'exception est
journalisée puis avalée, et l'apport du message est perdu sans que personne ne le
sache.

## Objective

Que l'enrichissement d'un contact praticien aboutisse quand deux messages
concernant le **même** praticien sont traités simultanément.

## Ce qui est établi

**Mesuré** — campagne task-255 du 2026-08-13, banc local, quatre occurrences par
série de trois tirs, reproduites sur **les deux** séries (hôte affamé et hôte
calme), sur des praticiens différents (`loadtest-1`, `-3`, `-5`, `-7`) :

```
[PractitionerContactService] ❌ Error creating/updating contact for DR Pierre DIDOT
System.InvalidOperationException: Collection was modified; enumeration operation may not execute.
   at Microsoft.EntityFrameworkCore.Internal.InternalDbSet`1.RemoveRange(IEnumerable`1 entities)
   at ContactRepository.UpdateAsync(ContactDto contact)          ContactRepository.cs:206
   at PractitionerContactService.UpdateWithConflictRetryAsync(…)  PractitionerContactService.cs:201
   at PractitionerContactService.EnrichContactAsync(…)            PractitionerContactService.cs:87
   at PractitionerContactService.CreateOrUpdateContactAsync(…)    PractitionerContactService.cs:52
```

Le corpus du banc adresse le **même praticien** depuis plusieurs messages, ce qui
explique que le défaut sorte à tous les coups sur une campagne d'enrichissement.

**Lu dans le code, et non mesuré** — c'est une lecture structurelle, à confirmer
par un test avant tout correctif : `ContactRepository.UpdateAsync` appelle

```csharp
db.ContactMssAddresses.RemoveRange(entity.MssAddresses);
db.ContactTags.RemoveRange(entity.Tags);
db.ContactGroupMembers.RemoveRange(entity.GroupMembers);
```

`entity.MssAddresses` est une **collection de navigation suivie par EF**.
`RemoveRange` marque chaque entité comme supprimée, ce qui déclenche le
raccordement des navigations — donc **modifie la collection qu'il est en train
d'énumérer**. L'énumérateur se plaint, exactement comme le ferait un
`foreach` qui supprime dans la liste qu'il parcourt.

**Ce que ça coûte** : l'exception remonte jusqu'à `CreateOrUpdateContactAsync`
qui la journalise en `Error` et **s'arrête là**. Le message a bien été enrichi,
mais le **contact** ne l'a pas été. Aucune alerte, aucun rejeu — le rejeu de
task-250 se déclenche sur `ConflictException`, un type qui n'est levé
**qu'après** `SaveChangesAsync`, donc jamais atteint ici.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que c'est le même défaut que task-250.** Celui-là était un
  conflit de concurrence **à l'écriture** ; celui-ci est une erreur d'énumération
  **avant** l'écriture. Les commentaires en place décrivent le premier — ne pas
  les confondre, ni les supprimer.
- **Ne pas remplacer le rejeu par une suppression ensembliste.** Le commentaire
  de task-250 explique pourquoi, et c'est un constat empirique :
  `ExecuteDeleteAsync` est **relationnel uniquement** et lève sur le provider
  InMemory dont dépendent les tests de ce dépôt. Un correctif qui rend le code
  testable seulement sur le provider le plus riche est refusé (leçon task-247).
- **Ne pas présumer que matérialiser la collection suffit** sans le prouver.
  C'est le correctif le plus probable, il tient en un appel — raison de plus pour
  exiger un **test qui échoue d'abord**.
- **Ne pas élargir aux contacts patient** sans mesure : `CreatePatientContact`
  suit un chemin voisin, mais aucune occurrence n'a été relevée. Vérifier, et
  dire ce qu'on trouve.

## Definition of Done

- [ ] Build passe (0 erreur), tests passent (0 échec)
- [ ] Un **test unitaire reproduit le défaut d'abord** (rouge sans le correctif,
      vert avec) : mise à jour d'un contact portant plusieurs adresses MSS,
      étiquettes et appartenances de groupe
- [ ] Le même contrôle couvre les **trois** collections (`MssAddresses`, `Tags`,
      `GroupMembers`) — corriger la première et oublier les deux autres laisserait
      le défaut en place
- [ ] Un test couvre le cas **concurrent** : deux enrichissements du même contact
      ; **les deux apports survivent** (c'est la promesse de task-250, qui ne doit
      pas être défaite)
- [ ] Le chemin **contact patient** est vérifié et le verdict écrit : même défaut
      corrigé, ou absence de défaut justifiée
- [ ] Les tests passent sur le provider **InMemory** utilisé par ce dépôt
- [ ] Le rejeu et la traduction `DbUpdateConcurrencyException` →
      `ConflictException` de task-250 sont **inchangés**
- [ ] Une campagne d'enrichissement au banc ne produit **plus aucune**
      `InvalidOperationException` depuis `ContactRepository`

## Manual Test Plan

- Monter le banc (skill `loadtest-skill`), seeder 8 praticiens × 20 messages
- Purger, préchauffer, puis lancer `tests/loadtest-k6/run.sh enrich --env VUS=8`
- **Ce qu'il faut voir dans Seq**, filtre
  `@Level = 'Error' and SourceContext like '%PractitionerContactService%'` :
  **zéro** événement, là où la campagne task-255 en produisait quatre par série
- Ouvrir la fiche d'un praticien destinataire de plusieurs messages depuis
  l'application : ses adresses MSS, étiquettes et groupes doivent être **complets
  et sans doublon**
- Contre-épreuve du test : revenir au code d'origine et vérifier que le test
  unitaire **échoue**

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — correction de défaut
- **Exigences DSR honorées** : aucune exigence nouvelle
- **INS** : ⚠️ un contact praticien porte des **données à caractère personnel**
  (nom, RPPS, adresses MSSanté). Aucun journal ni message d'exception ajouté par
  cette US ne doit en publier — le journal existant nomme déjà le praticien
  (`FullName`), ce qui est **à réduire** au passage : un identifiant technique
  suffit à diagnostiquer
- **Interop CI-SIS** : sans objet — le contact n'est pas un document clinique
- **Habilitations** : le cloisonnement « une base par praticien » est inchangé
- **Authentification PS / Consentement** : inchangés
- **Tracé PGSSI-S** : ⚠️ la perte silencieuse d'enrichissement est aussi un
  défaut de traçabilité — après correctif, un échec d'enrichissement de contact
  doit rester **visible** et non avalé
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : ⚠️ retirer le nom du praticien du journal d'erreur est
  une réduction de la donnée journalisée — à faire, pas à documenter seulement

## Branches
- `api-mail` (pushed) : fix/task-259-removerange-collection-modifiee — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-259-removerange-collection-modifiee
- `dtos-mss` (pushed, auto-included) : fix/task-259-removerange-collection-modifiee — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/fix/task-259-removerange-collection-modifiee

## Develop log

- **Repos touchés** : `api-mail` (`dtos-mss` branché par auto-inclusion, **aucun
  commit** — aucun contrat modifié).
- **DTOs / interop publiés** : aucun changement.
- **Commit** : `api-mail` fabc6c1 `fix(contact): l'enrichissement d'un contact ne
  passe plus sous concurrence — et le mécanisme n'est pas celui qu'on croyait`

### ⚠️ Le mécanisme supposé par le task file est FAUX — le test l'a dit

Le task file donnait sa lecture de code comme **« lu dans le code, et non mesuré —
à confirmer par un test avant tout correctif »** : `RemoveRange` marquerait chaque
entité supprimée, ce qui déclencherait le raccordement des navigations et
modifierait donc la collection en cours d'énumération.

**Confirmation faite, et négative.** Le premier test écrit — un contact portant
trois adresses MSS, trois étiquettes et deux appartenances de groupe, mis à jour
par le vrai dépôt sur InMemory — est **passé du premier coup, sans correctif**.
Marquer `Deleted` des entités `Unchanged` ne touche pas la collection de
navigation. La consigne du task file (« ne pas présumer que matérialiser la
collection suffit sans le prouver ») a donc fait exactement ce pour quoi elle
était écrite.

**Ce qui lève réellement** : la présence d'une entité **`Added`** dans la
collection au moment de l'énumération. EF fait passer une entité `Added` marquée
`Deleted` à **`Detached`** — « une entité ajoutée n'existe pas encore en base, il
n'y a rien à supprimer » — et le détachement la **retire de la collection de
navigation**, donc modifie la liste en cours de parcours.

**Comment cet état survient au banc, et pourquoi jamais en usage séquentiel** : le
`DbContext` est **mémoïsé par instance de dépôt** (task-231), donc partagé entre
deux enrichissements simultanés du même praticien. Le premier passage a déjà
exécuté `AddContactRelations` — ses enfants sont `Added` et **raccordés à la
collection suivie** — quand le second entre dans `RemoveRange`. Le corpus du banc
adresse le même praticien depuis plusieurs messages : d'où **quatre occurrences
par série**, et zéro hors concurrence.

La conséquence pratique est que le correctif reste celui que le task file
pressentait (`.ToList()`), mais **posé sur la bonne raison** — et qu'il couvre
désormais **toute** mutation de la collection suivie, pas seulement le cas
imaginé.

### Reproduction — rouge d'abord, vert ensuite

`UpdateAsyncSurvivesAnUnsavedRelationAlreadyAttachedToTheTrackedContact` pose
l'état de façon **déterministe et sans concurrence** (un enfant non enregistré est
rattaché au contact suivi avant l'appel), puis appelle le vrai `UpdateAsync`.

```
Échoué  UpdateAsyncSurvivesAnUnsavedRelationAlreadyAttachedToTheTrackedContact
System.InvalidOperationException : Collection was modified; enumeration operation may not execute.
   at System.Collections.Generic.List`1.Enumerator.MoveNext()
```

— **l'exception exacte du banc**, sur le fournisseur **InMemory**, sans
`ExecuteDeleteAsync` et sans dépendre du fournisseur le plus riche (leçon
task-247, exigée par le DOD). Verte après le `.ToList()`.

Un test à deux tâches sur un `DbContext` partagé a été **écarté délibérément** : il
n'éprouverait que la non-thread-safety d'EF, pas ce défaut.

### Verdict sur le chemin contact patient

**Même défaut, corrigé mécaniquement — aucune modification de code
supplémentaire.** `PatientContactService.EnrichContactAsync` appelle **le même**
`ContactRepository.UpdateAsync` (ligne 89) ; il n'a pas de chemin d'écriture
propre. Aucune occurrence n'avait été relevée au banc **parce que le corpus
n'adresse pas deux fois le même patient**, pas parce que ce chemin serait immunisé.
Épinglé par `APatientContactUpdateFollowsTheSamePathAndSurvivesToo`.

### Vérification locale

| Suite | Résultat |
|---|---|
| `dotnet build HealthPlatform.Api.Mail.sln` | ✓ 0 erreur, 0 avertissement |
| `mss.mail.domain.tests` | ✓ 136 / 136 |
| `mss.mail.infrastructure.tests` | ✓ 450 / 450 (dont **9 nouveaux**) |
| `mss.mail.api.tests` | ✓ 661 / 661 |
| `mss.mail.application.tests` | 2 123 / 2 124 — 1 rouge **pré-existant** (`AiPromptHelperTests`) |
| `mss.mail.integration.tests` | 397 / 402 — **5 rouges pré-existants**, cf. ci-dessous |

> ⚠️ **Les 5 rouges d'`integration.tests` sont apparus au passage de minuit, pas
> avec ce correctif.** Ils étaient **verts il y a deux heures** dans cette même
> session (402/402, task-256), sans qu'aucune ligne ne change entre-temps.
> Contre-épreuve `git stash` : **exactement les mêmes 5 échecs** sans le travail de
> cette task. Tous portent sur « les messages du jour »
> (`FilterTodayEmails`, `GetFolderTodayAsync`, `GetFolderNotSeenTodayAsync` ×2,
> `GetFolderTodayAsync_Inbox`), et tous échouent sur une **collection vide** — la
> signature d'un décalage de fuseau entre la date semée et la date filtrée : à
> 00 h passées en heure locale (UTC+2), la date UTC est encore la veille.
> **Finding F-259-1**, hors périmètre de cette task.

### DOD — auto-contrôle

- [x] Build 0 erreur, tests verts (hors rouges pré-existants tracés ci-dessus)
- [x] Test unitaire reproduisant le défaut **d'abord** (rouge sans correctif, vert
      avec) — et il a en prime **réfuté le mécanisme supposé**
- [x] Les **trois** collections couvertes (`MssAddresses`, `Tags`, `GroupMembers`)
- [x] Cas concurrent : les **deux apports survivent** (promesse de task-250 non défaite)
- [x] Chemin contact patient vérifié, **verdict écrit** ci-dessus
- [x] Tests verts sur le fournisseur **InMemory**
- [x] Rejeu et traduction `DbUpdateConcurrencyException` → `ConflictException`
      **inchangés** (diff : aucune ligne de ce bloc modifiée)
- [x] AIPD — nom du praticien retiré du journal d'erreur, échec **toujours visible**
      en `Error`, épinglé par test
- [ ] **Différé au test manuel (HAG)** : « une campagne d'enrichissement au banc ne
      produit plus aucune `InvalidOperationException` » — c'est une mesure au banc,
      pas une assertion de code.

- **Étape suivante** : `/forge-simplify task-259`

## Simplify log

- **Repos éligibles touchés** : `api-mail` (`dtos-mss` sans commit, et hors
  périmètre de toute façon — porteur de contrat).
- **Commit** : `api-mail` 35e3f81 `refactor(contact): le test de tailles dit ce
  qu'il réfute, plus ce qu'il supposait`
- **Re-validation** : build ✓ 0 erreur / 0 avertissement ; `infrastructure.tests`
  ✓ 450 / 450.

Une seule correction, sur l'axe **altitude** : le commentaire du `[Theory]`
justifiait encore les tailles de collection par le mécanisme **supposé** — celui
que ce même test venait de réfuter. Il dit désormais son objet réel : fermer
l'explication « ça ne se produit qu'au-delà de N relations » pour qui relira le
défaut. Un commentaire qui argumente une hypothèse morte est pire qu'absent : il
la remet en circulation.

Aucun autre écart sur ce diff — trois `.ToList()`, une ligne de journal, deux
fichiers de test. Rien à mutualiser, rien à alléger.

> **Finding F-259-2** — `MailRepositoryEnrichPersistInstrumentationTests`
> (`A_deduplicated_mail_is_measured_too_instead_of_vanishing_from_the_series`,
> task-258) est sorti **rouge une fois puis vert deux fois** sur la même
> révision, sans rapport avec ce correctif. C'est la **même famille** que le
> finding F-256-3 relevé la task précédente : le meter OpenTelemetry est statique,
> donc une classe qui capture ses mesures capte aussi celles des classes
> concurrentes. Le défaut existe donc aussi dans `infrastructure.tests`, pas
> seulement dans `application.tests` — ce qui renforce l'argument d'en faire une
> US à part entière plutôt que de le traiter classe par classe.

- **Étape suivante** : `/sonar task-259`

## Sonar log

Run **Mode A** (chaîné), `api-mail` sur `fix/task-259-removerange-collection-modifiee`.
Analyse complète (build Release + 5 projets de tests avec couverture OpenCover +
scanner). Conteneurs déjà démarrés au run précédent.

### KPIs qualité — baseline → final

| Métrique | Baseline (avant run) | Final | Cible |
|---|---|---|---|
| Bugs | 2 | **2** | 0 |
| Vulnérabilités | 0 | **0** | 0 ✓ |
| Code smells | 58 | **59** | — |
| Security hotspots | 5 | **0** | — ✓ |
| Couverture globale | 87,6 % | **87,7 %** | ≥ 95 % |
| Duplication | 0,3 % | **0,3 %** | < 3 % ✓ |
| Fiabilité | C | **C** | A |
| Sécurité | A | **A** | A ✓ |
| Maintenabilité | A | **A** | A ✓ |

### Quality Gate (new code) — `ERROR`, et **aucun finding attribuable à task-259**

| Condition | Avant | Après | Verdict |
|---|---|---|---|
| `new_coverage` | 88,0 % | **88,0 %** | ✓ OK (seuil 80 %) |
| `new_duplicated_lines_density` | 0,06 % | **0,06 %** | ✓ OK (seuil 3 %) |
| `new_security_hotspots_reviewed` | 100,0 % | **100,0 %** | ✓ OK (acquis au run task-256) |
| `new_violations` | 60 | **59** | ✗ ERROR (seuil 0) |

**Les quatre fichiers touchés par cette task ne portent qu'un seul finding, et il
est antérieur** — `csharpsquid:S2302` sur `ContactRepository.cs`, code de
task-250. Les 58 autres sont dans des fichiers que cette task n'ouvre pas.

**Le compte est parti de 60 et non de 59, et l'explication n'est pas une
régression** : cette branche ne contient pas le correctif `report.py` de task-256,
lequel remonte le littéral `"non relevé"` en constante de module et referme donc un
`python:S1192`. Sur `develop`, ce finding est encore ouvert — d'où 4 occurrences de
S1192 dans `report.py` ici contre 3 sur la branche task-256. **Le +1 est l'absence
d'une amélioration voisine, pas un ajout de dette.** Il se referme au merge de
la PR #188.

### Ce que le run a corrigé

**`csharpsquid:S2302` (`ContactRepository.cs`) classé FAUX POSITIF avec
justification.** La règle demande de remplacer le littéral `contact` par
`nameof(contact)` — mais le mot est ici de la **prose française** dans un message
d'exception destiné à l'exploitant (« Mise a jour concurrente du contact
{contactId} »), pas une référence au paramètre homonyme. Appliquer la règle
produirait « du contact contact 3fa8… » : elle confond un nom commun avec un
identifiant. Le message porte déjà l'identifiant utile (`contactId`). Traité
plutôt qu'ignoré, parce que la règle porte sur un fichier que cette task ouvre.

**Les security hotspots du projet sont à zéro** (5 → 0) : conséquence du run
task-256, où les 5 `TO_REVIEW` du new code ont été revus et classés `SAFE`.

### Phase 2 (dette legacy) — **skippée délibérément**, même motif qu'au run précédent

Corriger 58 findings répartis sur 14 fichiers sans lien avec un correctif de trois
`.ToList()` ferait franchir à la PR la limite de la règle 5 (~30 fichiers) et
violerait la règle 6 (périmètre isolé). Les 14 findings S3776 (12 Python + 2 JS)
sont de toute façon hors périmètre de `/sonar` — règle blacklistée, traitée par
`/sonar-s3776`, une méthode par PR.

> **Le finding F-256-4 reste ouvert et se confirme** : la new-code period
> `PREVIOUS_VERSION` héritée oblige chaque task à refaire à la main l'analyse de
> provenance pour savoir si *elle* a introduit de la dette. Deuxième task
> consécutive à devoir le faire.

- **Étape suivante** : `/lint-angular task-259`

## Lint log (client-angular)

⤍ **Skippé proprement** — `**Repos**: api-mail`, aucun code Angular écrit. Rien à
auto-fixer, rien à valider. Le filet des frontends appairés est désactivé.

- **Étape suivante** : `/lint-mobile task-259`

## Lint mobile log

⤍ **Skippé proprement** — aucun code mobile écrit. `Client/Mobile/` est sur
`develop`, arbre propre.

- **Étape suivante** : `/verify-visual task-259`

## Visual verify log

⤍ **Skippé proprement** — aucun écran `client-mobile` touché, aucun
`## Stitch design log` sur cette task.

- **Étape suivante** : `/review task-259`

## PRs

- `api-mail` — **#189** https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/189
  (label `awaiting-human-merge`, mergeable, `fix/task-259-removerange-collection-modifiee` → `develop`)
- `dtos-mss` — **aucune PR** : branche créée par auto-inclusion, aucun commit.
- Autres repos : non listés, non touchés. `devops`, `psc-proxy-*` : hors automation.

## Code Review Summary

**Verdict : APPROVED** — 4 fichiers revus, **0 blocage**, 1 suggestion non
bloquante. Détail complet dans le body de la PR #189.

| Axe | Verdict |
|---|---|
| Correctness | ✅ le seul changement de comportement est l'énumération d'un instantané ; la sémantique de **remplacement en bloc** est vérifiée explicitement, sans quoi un correctif qui aurait simplement cessé de supprimer serait passé |
| Sécurité / PGSSI-S | ✅ la donnée journalisée **diminue** ; aucun secret, aucune entrée externe |
| Architecture | ✅ le bloc de task-250 (rejeu + traduction `ConflictException`) est intact — vérifié sur le diff, aucune ligne modifiée |
| Qualité de code | ✅ le commentaire consigne le mécanisme **réel** et marque la lecture structurelle comme **réfutée** : sans cela, le prochain lecteur ré-adopterait l'explication fausse |
| Performance | ✅ trois `ToList()` sur des collections bornées par le nombre de relations d'un contact — négligeable devant l'aller-retour base qui suit |
| Couverture de test | ✅ 10 cas neufs, dont la reproduction déterministe de l'exception exacte du banc sur InMemory |

### Findings

1. **F-259-1 — 5 tests d'intégration « du jour » rouges au passage de minuit.**
   Verts deux heures plus tôt dans la même session, sans changement de code ;
   contre-épreuve `git stash` : mêmes 5 échecs sans le travail de cette task.
   Tous échouent sur une **collection vide** — signature d'un décalage de fuseau
   entre la date semée et la date filtrée (passé minuit en UTC+2, la date UTC est
   encore la veille). **Antérieur, hors périmètre.**
2. **F-259-2 — la collision de capture du meter existe aussi dans
   `infrastructure.tests`** (`MailRepositoryEnrichPersistInstrumentationTests`,
   rouge une fois puis vert deux fois sur la même révision). Même famille que
   F-256-3 : renforce l'argument d'en faire une US à part entière plutôt que de
   traiter classe par classe.
3. **F-259-3 — `PatientContactService` journalise l'INS en clair.** L'identifiant
   national de santé est bien plus sensible que le nom de praticien que cette PR
   vient de retirer côté praticien. **Non modifié délibérément** : contrairement au
   RPPS, l'INS n'a pas de substitut évident ici (aucun identifiant de contact n'est
   disponible au moment du `catch`), donc le remède demande une décision —
   pseudonymisation, identifiant de corrélation technique, ou acceptation
   argumentée. C'est ce que la vérification du chemin patient a trouvé.
4. **F-256-4 se confirme** — la new-code period `PREVIOUS_VERSION` héritée oblige
   chaque task à refaire à la main l'analyse de provenance. Deuxième task
   consécutive.

---

## Merged

**Date** : 2026-08-14 — `/merge task-259 --i-tested` (HAG, règle 10 : l'humain a
testé et attesté avant merge).

| Repo | PR | Commit squash sur `develop` |
|---|---|---|
| `api-mail` | [#189](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/189) | `20e8c8a` |
| `dtos-mss` | aucune PR — branche auto-incluse sans commit | — |

- Refs distantes `fix/task-259-removerange-collection-modifiee` supprimées sur
  `api-mail` et `dtos-mss` ; **branche locale conservée** sur `api-mail`.
- `develop` synchronisé sur les deux repos.
- CI `develop` api-mail : ✅ **verte** — run
  [31802545948](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/actions/runs/31802545948)
  (`completed / success`). Premier run éprouvant task-256 et task-259 ensemble :
  la CI de la PR #189 avait tourné avant l'arrivée de task-256 sur `develop`.
- **Branche staging `forge/staging-task-256-259-20260814` supprimée** (distante et
  locale, `api-mail`) : le lot 256-259 est intégralement mergé — plus aucune task
  active dans cet intervalle.
