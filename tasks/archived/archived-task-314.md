# todo-task-314.md — Une messagerie détachée n'offre plus que « Rattacher », et dit quand elle l'a été

**Repos**: dtos-mss, api-mail, client-blazor, client-angular, client-mobile
**Dependencies**: **task-310** (en attente de merge — elle touche les mêmes
`confirmRemove` sur les trois fronts ; à merger avant, sinon conflit d'édition
sur les mêmes blocs)
**Epic**: E016

## Objectif

Sur l'écran de gestion des messageries, une ligne **détachée** propose
aujourd'hui « Définir par défaut » et « Supprimer ». Les deux sont sans objet.
Elle ne doit plus offrir que **« Rattacher »**, et afficher la date à laquelle
elle a été **détachée** plutôt que celle de son rattachement.

## Le constat, du 2026-09-16

Capture d'écran à l'appui, sur `client-angular`, après avoir coché « Afficher
les messageries détachées ». La ligne affiche :

```
virginie.medecinrpps0062267@…   medecin.formation.mssante.fr   Détachée
Rattachée le 2026-09-16T07:52:32.309421+00:00
[ ☆ Définir par défaut ]  [ 🗑 Supprimer ]
```

**Quatre choses ne vont pas**, et elles se voient toutes sur cette seule ligne.

### 1. « Définir par défaut » n'a pas de sens

Une boîte détachée ne peut pas s'ouvrir, donc pas être le défaut. Si l'action
aboutissait, elle poserait un défaut que la garde d'entrée ne pourrait jamais
honorer — `MailboxEntryDecision` ne retient que les boîtes **sélectionnables**.

### 2. « Supprimer » n'a pas de sens, et induit en erreur

Elle est déjà détachée. Le bouton laisse croire à une seconde suppression, plus
définitive, **qui n'existe pas et ne doit pas exister** (voir l'encadré
ci-dessous). Le texte de confirmation dit d'ailleurs « La messagerie ne sera
plus accessible depuis ce compte » — c'est déjà le cas.

### 3. « Rattacher » manque, là où on l'attend le plus

La capacité existe et elle est soignée : `AttachMailboxAsync` **réactive la
ligne détachée** au lieu d'en créer une seconde, explicitement pour préserver le
`TenantId` que le journal d'audit référence. Mais le seul chemin est de
**retaper l'adresse** dans le formulaire du dessous — sur une ligne qui
l'affiche déjà.

### 4. La ligne d'information ment

Elle dit « Rattachée le … » sur une ligne marquée « Détachée ». Pour une boîte
détachée, la date qui compte est celle du **détachement** : c'est elle qui
gouverne la conservation, et c'est ce que la confirmation a promis au praticien
(« vos données restent soumises aux règles de conservation »). `detached_at`
existe en base et au domaine (`RegistryTenant.DetachedAt`) — il **manque au
contrat**.

Accessoirement, la date est rendue brute (`2026-09-16T07:52:32.309421+00:00`).

---

> ### ⚠️ Pourquoi « Supprimer » disparaît au lieu d'être réparé
>
> Question posée par l'humain le 2026-09-16 : « supprimer doit la retirer
> définitivement de la liste pour permettre à un autre compte de s'y rattacher ».
> Vérification faite, **la suppression ne serait ni nécessaire ni sans danger**.
>
> **Ce n'est pas l'adresse qui bloque un autre compte**, c'est le RPPS —
> `rppsHeldElsewhere` balaie toutes les lignes, détachées comprises. C'est un
> défaut distinct, traité par sa propre US.
>
> **Et supprimer la ligne orphelinerait le journal d'audit.** Elle porte le
> `TenantId` que `audit_traces.tenant_id` référence — 152 traces sur 5 tenants
> au moment du constat — et il n'existe **aucune clé étrangère** : la
> suppression n'échouerait pas, elle romprait le lien en silence. Ces traces
> sont soumises à la journalisation PGSSI-S et à 6 ans de conservation ; elles
> doivent rester attribuables.
>
> **Décision humaine du 2026-09-16** : pas de suppression. Le lien prime.

---

## Ce que la US NE fait pas

- **Le prédicat `rppsHeldElsewhere`** — une ligne détachée continue de retenir
  le RPPS et empêche un autre compte de rattacher la messagerie. C'est un
  **défaut réel**, mais backend et distinct : il mérite sa propre US, et le
  mêler ici brouillerait une correction d'écran avec une règle d'annuaire.
- **Aucune clé étrangère n'est ajoutée** sur `audit_traces`. Analysée et
  écartée : le rôle d'écriture (`mss_audit_writer`) n'a que `INSERT` et aucun
  droit sur le registre — une FK l'obligerait à lire la table référencée ; la
  vérification par ligne pèserait sur le puits groupé (correctif de capacité de
  task-300) ; et `CASCADE` effacerait des traces quand `RESTRICT` interdirait
  toute purge légitime. Une trace d'audit doit **survivre à son référent** :
  c'est l'inverse de ce qu'une FK affirme.
- **Aucun retrait d'affichage** (marqueur d'archivage). Écarté avec l'humain :
  une fois le RPPS libéré par l'US dédiée, une ligne détachée ne gêne plus rien
  — elle n'apparaît que si l'on coche la case.

## Definition of Done

### Le comportement, sur les trois fronts

- [ ] Une ligne dont l'état est **détaché** n'affiche **ni** « Définir par
      défaut » **ni** « Supprimer » — masqués, pas grisés : un bouton grisé
      annonce encore une action (arbitrage humain du 2026-09-15, déjà appliqué
      au « Par défaut » sur `client-mobile`)
- [ ] Elle affiche **« Rattacher »**, qui rattache l'adresse de la ligne par le
      chemin existant — donc **avec la sonde opérateur**, jamais en écrivant
      directement le registre
- [ ] Après un rattachement réussi, la ligne repasse **Active** et retrouve ses
      actions ordinaires, **sans rechargement de page**
- [ ] Une ligne **non détachée** garde exactement ses actions actuelles — c'est
      la contre-épreuve, et elle doit être testée
- [ ] La ligne détachée affiche **« Détachée le {date} »** au lieu de
      « Rattachée le {date} »
- [ ] Les dates sont **formatées** (locale `fr-FR`), plus d'ISO brut

### Le contrat

- [ ] `MailboxDto` porte `DetachedAt` (`DateTimeOffset?`, null si non détachée)
- [ ] `api-mail` le renseigne depuis `RegistryTenant.DetachedAt`
- [ ] Le paquet NuGet `dtos-mss` est publié et les consommateurs .NET bumpés
      (`api-mail`, `client-blazor`)
- [ ] Les modèles TypeScript de `client-angular` et `client-mobile` portent
      `detachedAt?: string`

### Les tests

- [ ] Un test par front : une ligne détachée n'expose **pas** les deux actions,
      et **expose** « Rattacher ». Vérifié **ROUGE** avant correction (rule 1)
- [ ] Un test par front sur la contre-épreuve : une ligne **active** conserve
      ses actions
- [ ] Un test par front : la ligne détachée affiche la date de **détachement**
- [ ] `api-mail` : un test vérifie que `DetachedAt` est renseigné pour une boîte
      détachée et **null** pour une boîte active
- [ ] Build + tests verts sur les cinq repos

### Ce qui ne doit pas bouger

- [ ] Le rattachement passe **toujours** par la sonde opérateur — aucun chemin
      qui écrirait le registre sans elle
- [ ] Le `TenantId` est préservé au re-rattachement (comportement existant de
      `AttachMailboxAsync`) : un test le fige si ce n'est pas déjà le cas

## Manual Test Plan

**Pré-requis** : un praticien avec une messagerie rattachée.
**Lancer** : `cd Api/Mail && aspire run --project src/AppHost`, puis le front.

1. Détacher la messagerie, puis cocher **« Afficher les messageries détachées »**
2. **Attendu** : la ligne détachée n'affiche **que** « Rattacher ». Ni « Définir
   par défaut », ni « Supprimer »
3. **Attendu** : elle indique **« Détachée le »** suivi d'une date lisible, pas
   d'un horodatage ISO
4. Cliquer **« Rattacher »**
5. **Attendu** : la sonde opérateur s'exécute, la ligne repasse **Active** et
   retrouve ses actions, sans rechargement de page
6. **Non-régression** : une messagerie active affiche toujours « Définir par
   défaut » et « Supprimer », et « Rattacher » n'y apparaît pas

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : MSSanté — lisibilité du parcours de gestion des
  adresses ; PGSSI-S § journalisation (conservation de l'imputabilité)
- **INS** : non applicable — aucune identité patient, aucun document
- **Authentification PS** : Pro Santé Connect / e-CPS, eIDAS substantiel —
  **inchangé**. Le rattachement conserve sa sonde XOAUTH2 : la US ne crée aucun
  chemin d'écriture du registre qui contournerait l'opérateur.
- **Habilitations** : RPPS porté par le jeton PSC — contrôle inchangé
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : rattachement et détachement restent journalisés à
  l'identique. **Le point central de cette US est conservatoire** : en retirant
  « Supprimer », elle protège le `TenantId` que les traces référencent. Aucune
  trace n'est retirée, aucune ne devient orpheline. Conservation 6 ans,
  inchangée.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement existant, inchangé
- **AIPD / impact RGPD** : inchangé. Aucune donnée nouvelle : `detached_at`
  existe déjà en base, la US l'expose au praticien qui en est le sujet.

## Branches

Branche unique : `feat/task-314-messagerie-detachee-rattacher`
(créée depuis `origin/develop` le 2026-09-16).

- `api-mail` (pushed) — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-314-messagerie-detachee-rattacher
- `client-blazor` (pushed) — https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-314-messagerie-detachee-rattacher
- `client-mobile` (pushed) — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-314-messagerie-detachee-rattacher
- `client-angular` (code-only) — la forge écrit sur la branche actuellement
  sortie dans `Client/Angular/`, soit `feature/nova-rewriting-mss` au moment du
  `/start`. L'humain garde branche, commit, push et PR TFS.
- `dtos-mss` (**branche non créée ici**) — première task sous la règle du
  2026-09-16 : `/start` ne crée plus de branche sur ce repo. C'est `/develop`
  qui la créera à son étape 2, puisque cette US **change bien le contrat**
  (`MailboxDto.DetachedAt`). La branche naîtra donc au moment où le contrat
  bouge, et sa seule présence signifiera qu'il a bougé.

Pré-flight du 2026-09-16 : `api-mail`, `client-blazor`, `client-mobile`,
`dtos-mss`, `sdk` sur `develop` et propres. Dépendance `task-310` archivée,
donc mergée — c'est elle qui a libéré ces repos.

## Timings

*(généré par `tools/timing/report.sh --task task-314 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 1 min 44 s | — | — | — | — |
| /develop | ok | 14 min 44 s | — | 4 (2 min 02 s) | — | api-mail 0B/1T, client-angular 0B/1T, client-blazor 0B/1T, client-mobile 0B/1T |
| /sonar | ok | 6 min 44 s | 1 (16 s) | 5 (3 min 53 s) | 1 (37 s) | api-mail 1B/5T |
| /lint-angular | ok | — | — | — | — | no start marker |
| /lint-mobile | ok | 19 s | — | — | — | — |
| /verify-visual | skipped | 14 s | — | — | — | pas de Stitch design log ; outillage Tools/visual-verify absent |
| /review | ok | 7 min 18 s | 5 (22 s) | 4 (2 min 16 s) | — | api-mail 1B/1T, client-blazor 1B/1T, dtos-mss 1B/0T, client-mobile 1B/1T, client-angular 1B/1T |
| /tech-writer | ok | 2 min 33 s | — | — | — | — |
| **Total cycle** | | **33 min 39 s** | **6 (38 s)** | **13 (8 min 12 s)** | **1 (37 s)** | |

Autres commandes mesurées : lint ×2 (14 s), nuget-wait ×1 (23 s)

## Sonar log

Scan du 2026-09-16 sur `feat/task-314-messagerie-detachee-rattacher`
(SonarQube 9.9.8, projet `healthplatform-api-mail`).

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| **Quality Gate (new code)** | OK | **OK** | = |
| New coverage | 85,8 % | **85,9 %** | +0,1 pt |
| New bugs / vulnérabilités | 0 / 0 | **0 / 0** | = |
| New code smells | 35 | 35 | = |
| Coverage projet | 87,8 % | 87,8 % | = |
| Duplication | 0,4 % | 0,4 % | = |
| Bugs / Vulnérabilités / Smells | 0 / 0 / 228 | 0 / 0 / 228 | = |
| Ratings (fiabilité / sécurité / maintenabilité) | 1.0 / 1.0 / 1.0 | 1.0 / 1.0 / 1.0 | = |

### Itérations de nettoyage : 0

Requête ciblée sur les deux seuls fichiers du diff `api-mail` —
`MailboxManagementService.cs` et son spec — : **0 issue ouverte**. Le diff se
réduit à une propriété mappée, son commentaire et deux tests.

Les 35 *new code smells* et les 228 du projet sont **antérieurs** à cette
branche.

5 passes instrumentées OpenCover, 4 479 tests verts, 0 échec.

### Note d'outillage

Le conteneur SonarQube était arrêté (`Exited (255)`, 4 h). Redémarré par
l'étape elle-même, **base d'abord** (`sonarqube_db` puis `sonarqube`) — le
piège mesuré à task-289 : démarrer `sonarqube` seul rend la main sans erreur,
puis le serveur meurt sur `UnknownHostException: sonarqube_db` et repasse en
`Exited (0)`. Le serveur est passé `STARTING` → `UP` en un poll.

## Lint log

**Étape** : `/lint-angular task-314` — mode A (chaîné), code-only.
**Périmètre** : `Client/Angular/front`, base `origin/next`, lint scopé
`--projects=tag:scope:mss`.

| Projet | Errors | Warnings |
|---|---|---|
| `mss-lib` | **0** | 41 |
| `mss` | 0 | 0 |
| `weda2` (hors scope de fix) | 0 | 14 |
| `design-system`, `dmp-lib` (hors scope) | 0 | 1 |

**Itérations de nettoyage : 0.** Baseline = final : **0 error**. La chaîne
n'avait rien à corriger — les fichiers touchés par task-314
(`core/models/mailbox.model.ts`, `features/mailbox-management/*.{ts,html,spec.ts}`)
ne portent aucune error.

Les 41 warnings de `mss-lib` sont de la **dette pré-existante**, répartie sur
26 fichiers : `jsdoc/require-example` (JSDoc sans bloc `@example`) et
`max-lines` sur `mss-api.service.ts` (2 320 lignes). Aucune n'est née de cette
task — le compte est identique à celui relevé avant `/develop`.

**Pas de re-build** : aucun fichier n'a été modifié par cette étape, et
l'arbre de travail est vert depuis la validation de `/develop`
(`mss-lib` 377 tests, `weda2` 2 573 tests).

Rappel code-only : aucune opération git sur `client-angular` — l'humain garde
la main sur la branche `feature/nova-rewriting-mss`, le commit, le push TFS et
l'ouverture de la PR.

## Lint mobile log

**Étape** : `/lint-mobile task-314` — mode A (chaîné), branche
`feat/task-314-messagerie-detachee-rattacher`.

`npm run lint` (`ng lint`, projet `app`) : **All files pass linting** —
0 error, 0 warning.

**Itérations de nettoyage : 0.** Rien à corriger, donc **aucun commit** :
l'arbre de travail est propre et l'état poussé (`0772309`) reste celui validé
par `/develop` (build vert, 856 tests verts). Les quatre fichiers du diff
(`core/models/mailbox.model.ts`, `mailbox/management/mailbox-management.page.{ts,html,spec.ts}`)
passent le lint sans réserve.

**Pas de re-build ni de re-test** : aucune modification apportée par cette
étape.

## Visual verify log

**Étape** : `/verify-visual task-314` — **skip propre**.

Deux motifs, chacun suffisant au pré-vol :

1. **Aucun `## Stitch design log`** dans cette task — `/develop` n'a pas
   généré d'écran mobile neuf. La modification de
   `mailbox-management.page.html` porte sur les actions et la date d'une ligne
   déjà existante, sans référence Stitch nouvelle à confronter.
2. **L'outillage `Tools/visual-verify/` n'est pas présent** dans ce plan de
   contrôle (ni `capture.mjs`, ni `screens.json`). Panne/absence d'outillage =
   best-effort explicite du skill : logué, la chaîne continue.

Conséquence : aucune capture, aucun PNG commité, `Docs/epics/img/screens/`
inchangé. La ligne détachée reste à vérifier à l'œil par l'humain au HAG —
elle figure au `## Manual Test Plan`.

## PRs

| Repo | PR | Label |
|---|---|---|
| `dtos-mss` | https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/33 | `awaiting-human-merge` |
| `api-mail` | https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/242 | `awaiting-human-merge` |
| `client-blazor` | https://github.com/codengine-technologies/HealthPlatform.Client/pull/79 | `awaiting-human-merge` |
| `client-mobile` | https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/75 | `awaiting-human-merge` |

**`client-angular` (code-only)** — l'humain gère commit/push TFS et l'ouverture
de la PR. Branche courante : `feature/nova-rewriting-mss`. Fichiers modifiés par
la task (non commités, par conception) :

- `front/libs/mss/src/core/models/mailbox.model.ts`
- `front/libs/mss/src/features/mailbox-management/mss-mailbox-management.component.ts`
- `front/libs/mss/src/features/mailbox-management/mss-mailbox-management.component.html`
- `front/libs/mss/src/features/mailbox-management/mss-mailbox-management.component.spec.ts`

Deux autres fichiers apparaissent modifiés dans l'arbre Angular
(`apps/mss/src/environments/environment.ts`, `apps/weda2/src/environments/environment.ts`)
— **étrangers à task-314**, à ne pas embarquer dans le commit.

## Code Review Summary

**Verdict : APPROVED** — 11 fichiers revus, 0 blocage, 2 suggestions.

### Ce qui est vérifié

- **Correction** — la décision « la ligne est-elle détachée ? » a **une seule
  source** par front (`isDetached` / `mailbox.State == MailboxStates.Detached`),
  qui gouverne à la fois les actions et la date. Dupliquer la comparaison dans
  le gabarit les aurait fait diverger le jour où un état s'ajoute.
- **Le rattachement passe par la sonde** — `accounts.attach(email)` /
  `AttachAsync`, le même chemin que l'ajout. Aucun nouveau chemin d'écriture du
  registre n'a été introduit ; un test par front le fige.
- **`TenantId` préservé** — comportement existant de `AttachMailboxAsync`, déjà
  figé par `PostgresTenantRegistryClientTests.ReattachingADetachedMailbox_KeepsTheSameTenantId`.
  Rien à ajouter (le DOD le prévoyait « si ce n'est pas déjà le cas »).
- **Contrat** — `DetachedAt` nullable, renseigné depuis `RegistryTenant.DetachedAt`,
  publié en `HealthPlatform.Dtos.Mss` **486.0.0**, consommateurs .NET bumpés et
  lock files alignés (`945914d1`).
- **Tests** — la **contre-épreuve** est présente sur les trois fronts (une ligne
  active garde ses actions et n'offre pas « Rattacher »). Sans elle, un
  `isDetached` toujours vrai aurait passé les autres tests.
- **Sécurité / i18n** — aucun secret, aucune entrée non validée ; Blazor passe
  par le `Localizer` (FR + EN ajoutés), Angular et mobile suivent le patron
  existant de leur écran.

### ⚠️ Suggestions (non bloquantes)

1. **`client-angular` — bloc JSDoc orphelin.** L'insertion des trois méthodes a
   laissé le doc de `stateLabel` (« Le libelle FR de l'etat de rattachement »)
   au-dessus de `isDetached` ; le doc correct est bien porté par `stateLabel`
   plus bas. Inerte — TypeScript et ESLint attachent le **dernier** bloc — mais
   trompeur à la lecture. À supprimer au moment du commit TFS. Non corrigé ici :
   `/review` ne patche pas de code (règle de la forge).
2. **Le drapeau `busy` n'est pas relâché dans un `finally`.** Une erreur réseau
   pendant `reattach` laisse l'écran figé en « occupé ». **Défaut du patron
   existant**, partagé à l'identique par `setDefault` et `retryAuth` sur les
   trois fronts — pas introduit par cette task. À traiter d'un bloc dans une US
   dédiée plutôt qu'en exception locale.

## Merged

Mergée le 2026-09-16 par l'humain (`/merge task-314 --i-tested`, HAG règle 10),
squash dans l'ordre topologique `dtos-mss → api-mail → client-blazor →
client-mobile`.

| Repo | PR | Squash sur `develop` |
|---|---|---|
| `dtos-mss` | #33 | `fc0f8a3` |
| `api-mail` | #242 | `c8ade42b` |
| `client-blazor` | #79 | `58cad05` |
| `client-mobile` | #75 | `806e213` |

Branches `feat/task-314-messagerie-detachee-rattacher` supprimées **distantes et
locales** sur les quatre repos (règle du 2026-09-16 : conserver la branche locale
faisait refuser le pré-flight du `/start` suivant).

**CI `develop` vertes** sur les quatre repos, vérifiées après merge.

**`client-angular` reste à la charge de l'humain** — les quatre fichiers de la
task sont toujours non commités sur `feature/nova-rewriting-mss` (mode
code-only). Le clone Angular n'a **pas** été basculé sur `develop` : la forge ne
change jamais de branche à la place de l'humain.

Aucune branche staging à nettoyer : ce cycle n'est pas passé par `/forge`.
