# todo-task-310.md — Supprimer la messagerie ouverte laisse une session IMAP orpheline chez l'opérateur

**Repos**: client-angular, client-blazor, client-mobile
**Dependencies**: **task-303** (mergée — elle a posé la rotation d'identifiant de session
et la fermeture de la session sortante), **task-304** (mergée — elle a livré l'écran de
gestion et sa suppression). Aucune dépendance sortante.
**Epic**: E016
**Priorité**: **2** — rien ne casse à l'écran et aucune donnée n'est en jeu. Mais une
connexion reste ouverte chez l'opérateur MSSanté pour une messagerie que le praticien
croit avoir retirée, et elle s'y lit comme une session fantôme.

## Objective

Fermer la session de messagerie **avant** de détacher la boîte, et non après.

Aujourd'hui l'ordre est inversé : la fermeture part avec les en-têtes d'une boîte qui
vient d'être détachée, le backend la refuse, et le pool IMAP n'est jamais fermé
proprement.

## Le défaut, tracé dans le code

Constaté le 2026-09-14 en répondant à la question « si je supprime la messagerie sur
laquelle je suis connecté, comment le logiciel réagit ? ».

**La séquence actuelle**, identique sur les trois fronts
(`confirmRemove` / `ConfirmRemoveAsync`) :

```
1. DELETE /api/v1/account/mailboxes/{tenantId}   → state = Detached
2. reload de la liste
3. si c'etait la COURANTE → switchTo(repli)
     3a. sessionCloser()   ← POST /api/v1/sync/logout
                             avec Client-Email = la boite QUI VIENT D'ETRE DETACHEE
     3b. purge, nouvel identifiant de session, bascule
```

**L'étape 3a échoue, systématiquement.** Le middleware résout `Client-Email` contre le
registre, trouve le rattachement en `Detached`, et `MailboxSelectionService` répond
`NotCompatible` (`MailboxSelectionService.cs:65`). La requête est **refusée avant
d'atteindre le contrôleur**, donc `BackgroundSyncManager.CleanupUserAsync` n'est jamais
appelé.

> ⚠️ **Rédaction corrigée le 2026-09-16.** Cette phrase disait « `POST /api/v1/sync/logout`
> ne porte pas `[MailboxNotRequired]` ». Ce n'est plus vrai — **task-313 a posé l'attribut
> sur cette route**, et c'est mergé. La conclusion, elle, est **inchangée**, et c'est le
> point à retenir : l'attribut n'exempte **qu'une seule** issue de sélection.
>
> ```csharp
> // UserContextEnricherMiddleware — ApplyMailboxSelectionAsync
> if (!mailboxRequired && selection.Outcome == MailboxSelectionOutcome.MailboxRequired)
> {
>     return false;   // seule MailboxRequired passe
> }
> // NotAttached, NotCompatible, PscIdentityConflict → 403
> ```
>
> Une boîte **détachée** rend `NotCompatible`, jamais `MailboxRequired`. Elle reste donc
> refusée, attribut ou pas. Le défaut décrit par cette US est intact.

Le front l'avale — c'est du best-effort, et c'est délibéré :

```ts
try { await this.sessionCloser() }
catch (error) {
    console.error('[MailboxSession] Failed to close the outgoing session', error)
}
```

### Ce que ça coûte

Le pool IMAP de la boîte supprimée **reste connecté chez l'opérateur MSSanté** jusqu'à son
propre délai d'expiration. C'est exactement le « pool IMAP orphelin » que la rotation
d'identifiant de session de task-303 existe pour éviter :

> *Le backend lie un `Client-Session-Id` à la première boîte qu'il a ouverte et refuse en
> 409 le même identifiant présenté avec une autre boîte, **précisément pour qu'une bascule
> ne laisse pas un pool IMAP orphelin**.*

La suppression est le **seul** chemin qui le produise, parce que c'est le seul où la boîte
sortante cesse d'être valide **avant** qu'on essaie de la fermer. Une bascule ordinaire ou
une déconnexion ferment toutes deux une boîte encore rattachée, et aboutissent.

### Un TROISIÈME chemin, apparu depuis — et mesuré

Ajouté le 2026-09-16. Cette US décrivait un seul chemin fautif ; il y en a désormais deux,
et le second n'existait pas à sa rédaction.

**task-312 / task-313** ont livré la déconnexion complète au détachement de la **dernière**
messagerie. Sa séquence est : `session.clear()` — qui vide la boîte courante — puis l'ordre
de clôture. La requête part donc **sans `Client-Email`**, rend `MailboxRequired`, et
l'attribut posé par task-313 la laisse passer. Elle **aboutit en 200**.

Mais elle ne ferme rien. `CleanupUserAsync` n'utilise l'adresse que comme **clé de
recherche** (`RemoveSession`, `HasActiveSessionsForEmail`, `TryGetValue`, `GetStateAsync`) :
avec une chaîne vide, aucune correspondance. Mesuré dans Seq le 2026-09-15 à 22:01:15, sur
une déconnexion réelle depuis un iPhone :

```
POST /api/v1/sync/logout — LogoutCleanupAsync
  Email = ""            UserEmail = "unknown"
  SessionsClosed = 0     ← six fois (l'ordre est diffusé aux réplicas)
```

**Le correctif de task-313 a rendu la requête silencieuse sans la rendre efficace.** Il a
supprimé le 403 et le toast affiché pendant une déconnexion volontaire — ce qu'il visait —
mais le pool IMAP reste ouvert, comme sur l'autre chemin.

| Chemin | Ferme la session IMAP ? |
|---|---|
| Déconnexion ordinaire, messagerie ouverte | ✅ oui — `SessionsClosed=1` |
| Détacher la courante, un repli existe | ❌ 403 `NotCompatible`, contrôleur jamais atteint |
| Détacher la **dernière** (depuis task-313) | ❌ 200, mais `SessionsClosed=0` — **mesuré** |

**Les deux chemins fautifs ont la même cause et le même remède** : on essaie de fermer une
session quand on ne sait plus laquelle. Fermer **avant** de détacher les règle tous les
deux d'un coup, puisqu'à cet instant la boîte est encore rattachée et l'adresse encore
résolue.

> **Ce n'est pas un défaut de sécurité.** La session IMAP orpheline appartient au
> praticien lui-même, elle expire seule, et aucune donnée ne fuit. C'est un défaut de
> **propreté d'exploitation** : elle consomme une connexion chez l'opérateur, et elle se
> lit dans ses journaux comme une session que personne n'a fermée.

## Le correctif — fermer tant que la boîte est encore valide

**Inverser l'ordre** : fermer la session, **puis** détacher.

```
1. si c'est la COURANTE → sessionCloser()    ← la boite est encore Active, l'appel aboutit
2. DELETE /api/v1/account/mailboxes/{tenantId}
3. reload de la liste
4. adopter le repli avec un identifiant de session NEUF
```

### Le piège de l'étape 4 — ne pas fermer deux fois

`switchTo()` appelle **lui-même** le `sessionCloser` (c'est l'étape 2 de sa séquence §D).
L'utiliser à l'étape 4 rejouerait la fermeture sur une boîte désormais détachée, et
reproduirait exactement le défaut qu'on corrige — une deuxième fois, en silence.

Le store expose déjà les primitives nécessaires : `open(mailbox)` pose la boîte courante et
tire un identifiant neuf **sans rien fermer**, et `clear()` purge l'état local. Le chemin
de suppression doit passer par là, ou par une variante explicite de `switchTo` qui sait que
la sortante est **déjà fermée**.

### L'attribut `[MailboxNotRequired]` — consigne révisée le 2026-09-16

Cette US écrivait : *« Ce qu'il ne faut pas faire : marquer `sync/logout` en
`[MailboxNotRequired]`. La route saurait alors être appelée sans boîte résolue — donc sans
savoir quelle session IMAP fermer. On déplacerait le défaut du front vers le backend. »*

**task-313 l'a fait quand même, et c'est mergé.** La consigne était juste, et la mesure lui
a donné raison : `SessionsClosed = 0` est exactement le défaut déplacé vers le backend.
Mais task-313 répondait à un autre problème, réel lui aussi — sans l'attribut, le praticien
qui détache sa dernière messagerie voyait une **erreur 403 pendant une déconnexion
volontaire**, et n'avait plus aucun chemin de retour vers le rattachement.

**Les deux exigences se concilient, et c'est cette US qui les concilie :**

- Une fois la fermeture déplacée **avant** le détachement, la session utile est fermée à un
  instant où l'adresse **est** résolue — `SessionsClosed=1`.
- Ce qui reste ensuite, c'est une déconnexion d'un compte qui n'a **plus aucune** messagerie.
  Il n'y a alors rien à fermer : que la route aboutisse en no-op est correct, et l'attribut
  ne fait qu'éviter un refus inutile.

**L'attribut RESTE donc en place. Il cesse d'être un problème parce que la fermeture utile
a déjà eu lieu ailleurs.** Ne pas le retirer — ce serait rouvrir le défaut de task-313
sans refermer celui-ci.

> **Conséquence sur le périmètre :** cette US reste **exclusivement front**. Aucun
> changement backend n'est nécessaire, et l'attribut posé par task-313 n'est pas à toucher.

## Definition of Done

### Le comportement, sur les trois fronts

- [ ] Lors de la suppression de la messagerie **courante**, la fermeture de session part
      **avant** l'appel de détachement, et elle **aboutit** (200, pas de refus)
- [ ] La fermeture n'est appelée **qu'une fois** par suppression. Le repli est adopté sans
      rejouer de fermeture sur une boîte détachée
- [ ] Supprimer une messagerie qui **n'est pas** la courante ne déclenche **aucune**
      fermeture de session — le comportement actuel est correct et ne doit pas changer
- [ ] Les trois issues existantes sont préservées : repli sur la boîte par défaut héritée,
      sinon `select` s'il reste une boîte sélectionnable, sinon `onboarding`
- [ ] L'identifiant de session est **neuf** après la suppression de la courante : le
      backend refuse en 409 `SESSION_MAILBOX_MISMATCH` un identifiant présenté avec une
      autre boîte

### Les tests — c'est l'ordre qui est testé, pas seulement le résultat

- [ ] **`client-angular`**, **`client-mobile`**, **`client-blazor`** — un test par front
      vérifie l'**ordre des appels** : fermeture de session **puis** détachement. Un test
      qui se contenterait de vérifier que les deux ont eu lieu passerait aussi sur le code
      défectueux
- [ ] Un test par front vérifie qu'une suppression de boîte **non courante** n'appelle
      **pas** la fermeture
- [ ] Un test par front vérifie que la fermeture n'est appelée **qu'une fois** quand la
      courante est supprimée et qu'un repli existe — c'est la contre-épreuve du piège
      `switchTo`
- [ ] Build + tests verts sur les trois fronts

### Ce qui ne doit pas bouger

- [ ] `POST /api/v1/sync/logout` **conserve** le `[MailboxNotRequired]` posé par task-313 —
      critère **inversé le 2026-09-16** : il exigeait l'inverse, avant que task-313 ne pose
      l'attribut pour une autre raison, valable. Le retirer rouvrirait le 403 affiché
      pendant la déconnexion de la dernière messagerie. Voir « L'attribut
      `[MailboxNotRequired]` — consigne révisée »
- [ ] **Le chemin de la DERNIÈRE messagerie ferme lui aussi la session** : la clôture part
      avant `session.clear()`, donc tant que l'adresse est encore résolue. Vérifiable dans
      Seq — `SessionsClosed=1` au lieu du `0` mesuré le 2026-09-15
- [ ] Aucun changement backend. Le diff se limite aux trois fronts
- [ ] La déconnexion (`MAIL_SESSION_CLOSER`, task-285) et la bascule ordinaire
      (`switchTo`, task-303 §D) sont **inchangées** : leurs tests existants restent verts
      sans modification d'assertion

## Manual Test Plan

- **Lancer** : `cd Api/Mail && aspire run --project src/AppHost`, puis le front à tester.
- **Préparer** : un praticien avec **deux** messageries MSSanté de formation rattachées,
  l'une par défaut.
- **Actions et vérifications** :
  1. Ouvrir la messagerie **non par défaut** (bascule via le sélecteur) — c'est elle qu'on
     va supprimer, pour que le repli soit non trivial.
  2. Aller dans la gestion des messageries, supprimer **celle sur laquelle on est**,
     confirmer.
  3. **Attendu à l'écran** : la bascule s'opère vers la messagerie restante, la boîte de
     réception se recharge dessus. Aucun message d'erreur.
  4. **Attendu dans les journaux serveur (Seq)** : une trace `MailboxSessionClosed` portant
     l'adresse **supprimée**, suivie de `MailboxDetached`, puis `MailboxSessionOpened` sur
     la messagerie de repli. **Dans cet ordre.**
  5. **Attendu dans la console du navigateur** : **aucun** `[MailboxSession] Failed to
     close the outgoing session`. C'est la ligne qui signe le défaut aujourd'hui.
  6. **Contre-épreuve** : supprimer maintenant la messagerie **non courante** → aucune
     trace `MailboxSessionClosed`, la session en cours n'est pas touchée, on reste sur
     place.
  7. **Cas de la dernière** : supprimer la dernière messagerie restante → fermeture tracée,
     puis retour à l'écran d'onboarding.
- **Données de test** : praticien synthétique du realm de formation, deux adresses MSSanté
  de formation. Aucune donnée de santé réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correction de propreté d'exploitation sur un mécanisme
  existant
- **Exigences DSR honorées** : non applicable — aucun échange, aucun document
- **INS** : non applicable — aucun patient manipulé
- **Authentification PS** : inchangée. La suppression exige déjà une session Pro Santé
  Connect active ; cette US ne touche ni la condition ni le contrôle
- **Habilitations** : inchangées — aucune route nouvelle, aucun contrôle d'accès modifié
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : **amélioré, et c'est une partie du sujet.** `MailboxSessionClosed`
  est aujourd'hui **absente** du journal quand on supprime la boîte courante, puisque la
  requête qui l'écrit est refusée. La frontière de session est donc incomplète : le journal
  montre une messagerie ouverte que rien ne ferme. Après cette US, toute session ouverte a
  sa fermeture tracée, y compris sur ce chemin. Durée de conservation inchangée
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — aucun flux, aucune donnée déplacée
- **AIPD / impact RGPD** : inchangé. Aucune donnée personnelle nouvelle. La correction
  **réduit** la durée de vie d'une connexion authentifiée chez un tiers, ce qui va dans le
  sens de la minimisation

### DOD santé applicable

- [ ] `MailboxSessionClosed` est journalisée pour **toute** session de boîte ouverte, y
      compris quand la boîte est supprimée pendant qu'elle est ouverte — vérifié dans Seq
      au test manuel
- [ ] Aucune adresse MSSanté n'apparaît dans la console du navigateur ni dans un journal
      front

## Ce que cette US n'est pas

- **Pas un correctif de sécurité.** La session orpheline appartient au praticien lui-même,
  elle expire seule, et aucune donnée ne fuit. C'est de la propreté d'exploitation et de la
  complétude du journal.
- **Pas un assouplissement de `sync/logout`.** La route continue d'exiger une boîte
  résolue. La rendre appelable sans boîte déplacerait le défaut vers le backend, qui ne
  saurait plus quelle session IMAP fermer.
- **Pas une refonte de la séquence de bascule.** `switchTo` (task-303 §D) et la déconnexion
  (task-285) ne bougent pas. Seul le chemin de **suppression** change d'ordre.
- **Pas une correction backend.** Le serveur se comporte correctement : il refuse une
  requête portant une boîte détachée, et il a raison de le faire.

## Branches

Branche unique : `feat/task-310-fermer-session-avant-detachement`
(créée depuis `origin/develop` le 2026-09-16).

- `client-blazor` (pushed) — https://github.com/codengine-technologies/HealthPlatform.Client/tree/feat/task-310-fermer-session-avant-detachement
- `client-mobile` (pushed) — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-310-fermer-session-avant-detachement
- `dtos-mss` (pushed, auto-inclus car `client-blazor` est listé) — branche de
  précaution : la US est exclusivement front et ne change **aucun** contrat.
  Sans commit, aucune PR ne sera ouverte.
- `client-angular` (code-only) — la forge écrit sur la branche actuellement
  sortie dans `Client/Angular/`, soit `feature/nova-rewriting-mss` au moment du
  `/start`. L'humain garde branche, commit, push et PR TFS.

Pré-flight du 2026-09-16 : `api-mail`, `client-blazor`, `client-mobile`,
`dtos-mss`, `sdk` sur `develop` et propres. Dépendances `task-303` et
`task-304` archivées, donc mergées.

**`api-mail` n'est pas listé et ne doit pas l'être** : la consigne révisée du
2026-09-16 conclut que l'attribut `[MailboxNotRequired]` posé par task-313
**reste en place**. Le diff est exclusivement front.

## Timings

*(généré par `tools/timing/report.sh --task task-310 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 37 s | — | — | — | — |
| /develop | ok | 13 min 18 s | 1 (25 s) | 3 (45 s) | — | client-mobile 0B/1T, client-blazor 0B/1T, client-angular 1B/1T |
| /lint-angular | ok | 2 min 16 s | 1 (20 s) | 1 (14 s) | — | 1 itération(s), client-angular 1B/1T |
| /lint-mobile | ok | 29 s | — | — | — | 0 erreur des la baseline |
| /verify-visual | skipped | 12 s | — | — | — | aucun Stitch design log (aucun template touche) + Tools/visual-verify absent |
| /review | ok | 3 min 51 s | 3 (26 s) | 3 (33 s) | — | client-blazor 1B/1T, client-mobile 1B/1T, client-angular 1B/1T |
| /tech-writer | ok | 1 min 16 s | — | — | — | — |
| **Total cycle** | | **22 min 03 s** | **5 (1 min 12 s)** | **7 (1 min 33 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : lint ×2 (26 s)

## Lint log

`npx nx run-many -t lint --projects=tag:scope:mss` sur le working tree de
`Client/Angular/front/` (code-only — aucune opération git sur ce repo).

| | Erreurs | Warnings |
|---|---|---|
| Baseline (avant `/develop`) | 0 | 41 |
| Après le code de la feature | **3** | 43 |
| Final | **0** | **41** |

Les 3 erreurs et les 2 warnings supplémentaires étaient **les miens**, tous sur
le même bloc : un paramètre objet ajouté à `switchTo(mailbox, options?)` sans
mettre à jour son JSDoc. Corrigés pendant `/develop` (les erreurs) et à
l'itération 1 de cette étape (les `@example`).

**Retour à la baseline exacte : le diff de cette US ne contribue aucun finding.**
Les 41 warnings restants sont antérieurs et ne portent sur aucune ligne touchée.

Itérations : 1. Filet anti-régression après l'itération — `mss-lib` 371 tests
verts, build `weda2` OK.

### Boucle d'auto-amélioration

`conventions/angular.md` → `jsdoc/require-jsdoc` passe à **3 occurrences**. La
fiche disait déjà « modifier une signature, c'est modifier son JSDoc » — la
récidive confirme la règle plutôt qu'elle ne l'invalide. Le **détail nouveau**
consigné : un paramètre objet exige un `@param` par sous-propriété
(`@param options.maPropriete`), `@param options` seul ne suffisant pas.

## Lint mobile log

`npm run lint` (`ng lint`) sur `feat/task-310-fermer-session-avant-detachement` :
**« All files pass linting »** — 0 erreur, 0 warning, dès la baseline.

Itérations : 0. Aucun correctif, donc aucun commit et rien à pousser. Le filet
anti-régression n'avait pas à être rejoué : le repo est vert depuis `/develop`
(853 tests, build OK) et n'a pas bougé depuis.

À noter, par contraste avec `client-angular` : la configuration ESLint de
`client-mobile` ne porte pas les règles `jsdoc/*`. Le même diff — un paramètre
objet ajouté à `switchTo` — y passe donc sans remarque, alors qu'il a produit
3 erreurs côté Angular. C'est une divergence de configuration connue, déjà
consignée dans `conventions/angular.md`, pas un oubli de cette étape.

## Visual verify log

**Skip best-effort.** Deux motifs, comme pour task-313 :

1. **Aucun `## Stitch design log`** — condition de skip documentée. Le diff
   mobile ne touche **aucun template** : `git diff --stat origin/develop...HEAD`
   ne liste que quatre `.ts` (deux services, la page, son spec). Aucun `.html`,
   aucun `.scss`.

2. **L'outillage n'est pas installé sur ce poste** : `Tools/visual-verify/`
   n'existe pas. Panne d'outillage = best-effort par la règle de l'étape.

### Le risque de rendu est ici plus faible que sur task-313

task-313 ajoutait une **injection** à la page (`inject(LogoutService)`), ce qui
peut produire un écran blanc qu'aucun test unitaire ne voit. Cette US n'en
ajoute aucune : elle ne fait qu'appeler une méthode de plus sur un service
**déjà injecté**, et change la signature d'une autre. Une erreur y serait une
erreur de compilation TypeScript, pas une panne d'injection au montage.

Le parcours reste couvert par les étapes du `## Manual Test Plan`, qui ouvrent
réellement l'écran et vérifient dans Seq que `SessionsClosed` passe à 1.

Écrans capturés : 0.

## PRs

| Repo | PR | Label |
|---|---|---|
| `client-blazor` | https://github.com/codengine-technologies/HealthPlatform.Client/pull/78 | `awaiting-human-merge` |
| `client-mobile` | https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/74 | `awaiting-human-merge` |
| `dtos-mss` | **aucune PR** — 0 commit : la US ne change aucun contrat | — |

**`client-angular` (code-only)** — l'humain gère commit/push TFS et l'ouverture
de la PR. Branche au moment du cycle : `feature/nova-rewriting-mss`. Fichiers
modifiés (hors `environment.ts`, qui appartiennent à l'humain) :

```
front/libs/mss/src/core/stores/mailbox-session.store.ts
front/libs/mss/src/features/mailbox-management/mss-mailbox-management.component.ts
front/libs/mss/src/features/mailbox-management/mss-mailbox-management.component.spec.ts
```

## Code Review Summary

**Verdict : APPROVED** — 10 fichiers relus, 0 blocage, 1 suggestion.

| Front | Verdict |
|---|---|
| `client-blazor` · interface + service + page + 2 specs | ✅ ordre correct, drapeau explicite ; ⚠️ une suggestion (ci-dessous) |
| `client-mobile` · 2 services + page + spec | ✅ |
| `client-angular` · store + composant + spec | ✅ |

### ⚠️ Suggestion non bloquante — Blazor

`CloseCurrentSessionAsync(CancellationToken cancellationToken = default)`
**n'utilise pas son jeton** : `CloseServerSessionAsync()` n'en accepte aucun.
Un paramètre qui ne fait rien, sur une méthode d'interface toute neuve. Deux
issues : le retirer, ou propager le jeton. Non corrigé ici — `/review` ne
modifie pas de code. Sonar ne tournant pas sur `client-blazor`, rien ne
l'attrapera automatiquement.

### Le critère du DOD sur les assertions, précisément

Le DOD exigeait que la déconnexion et la bascule ordinaire restent vertes
« sans modification d'assertion ». **Tenu pour la bascule ordinaire** :
`MailboxSessionServiceTests` et `MailboxSwitcherComponentTests` sont
**intacts** — les paramètres optionnels préservent leurs appels existants.

Des assertions **ont** été modifiées, et il faut le dire : une par front sur le
chemin de **détachement** (`switchTo(fallback)` gagne son second argument), plus
des formes de matchers NSubstitute côté Blazor. Ce sont des mises à jour de
**signature** sur le chemin que cette US change délibérément, pas des
assouplissements.
