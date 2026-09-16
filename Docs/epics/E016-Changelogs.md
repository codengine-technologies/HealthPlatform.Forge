# E016 — Changelogs (vue ingénierie)

> **Audience** : équipes techniques, backlog, dette.
> **Document frère (vue produit)** : [`E016-socle-multi-tenant.md`](./E016-socle-multi-tenant.md)
> **Dernière mise à jour** : 2026-09-15 (task-309, task-311, task-312)

Historique détaillé des changements de l'EPIC **E016 — Socle multi-tenant**.
Une entrée par task ayant atteint `done-*` ou `archived-*`. Append-only : une
entrée existante n'est jamais réécrite.

---

## Historique détaillé des changelogs

### v1.11 — task-310 : la session de messagerie se ferme AVANT le détachement (`client-angular`, `client-blazor`, `client-mobile`)

> PRs : [client-blazor #78](https://github.com/codengine-technologies/HealthPlatform.Client/pull/78),
> [client-mobile #74](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/74).
> `client-angular` en code-only — l'humain commite et ouvre la PR TFS.

#### Ce que l'US ferme

L'ordre était inversé : la clôture de session partait **après** le détachement,
donc avec l'adresse d'une boîte que le registre venait de passer en `Detached`.
Le middleware la résout, la juge non sélectionnable, et répond `NotCompatible` —
un **403 qui n'atteint jamais le contrôleur**. `CleanupUserAsync` n'était donc
jamais appelé, et le **pool IMAP restait connecté chez l'opérateur MSSanté**
jusqu'à sa propre expiration.

Ce n'est pas un défaut de sécurité : la session orpheline appartient au
praticien, elle expire seule, aucune donnée ne fuit. C'est un défaut de
**propreté d'exploitation** — une connexion consommée chez l'opérateur, et une
session qui se lit dans ses journaux comme n'ayant jamais été fermée.

#### Deux chemins fautifs, et le second a été MESURÉ

La US en décrivait un. Il y en avait deux au moment de l'implémenter.

| Chemin | Avant | Après |
|---|---|---|
| Déconnexion ordinaire, messagerie ouverte | ✅ ferme | inchangé |
| Détacher la courante, un repli existe | ❌ 403 `NotCompatible` | ✅ ferme |
| Détacher la **dernière** (depuis task-312/313) | ❌ 200 mais `SessionsClosed=0` | ✅ ferme |

**Le troisième n'existait pas à la rédaction.** La déconnexion complète livrée
par task-312/313 émettait sa clôture après `session.clear()`, donc **sans
adresse du tout** : la requête aboutissait en 200 et ne fermait rien,
`CleanupUserAsync` n'utilisant l'adresse que comme clé de recherche. Mesuré dans
Seq le 2026-09-15 à 22:01:15, sur une déconnexion réelle :

```
POST /api/v1/sync/logout — LogoutCleanupAsync
  Email = ""            UserEmail = "unknown"
  SessionsClosed = 0     ← six fois (l'ordre est diffusé aux réplicas)
```

**task-313 avait rendu la requête silencieuse sans la rendre efficace** : elle
avait supprimé le 403 et le toast affiché pendant une déconnexion volontaire —
ce qu'elle visait — mais le pool restait ouvert. Les deux chemins ont la même
cause (on ferme quand on ne sait plus quoi) et le même remède.

#### La prémisse de la US avait péri, la conclusion non

Le task file affirmait que `POST /sync/logout` ne porte pas
`[MailboxNotRequired]`. Faux depuis task-313, qui l'a posé. Mais l'attribut
n'exempte **qu'une seule** issue de sélection :

```csharp
if (!mailboxRequired && selection.Outcome == MailboxSelectionOutcome.MailboxRequired)
{
    return false;   // seule MailboxRequired passe
}
// NotAttached, NotCompatible, PscIdentityConflict → 403
```

Une boîte détachée rend `NotCompatible`. Elle reste donc refusée, attribut ou
pas — le défaut décrit était intact. Vérification menée le 2026-09-16 à la
demande de l'humain, qui doutait de l'actualité de la US.

#### Une consigne de la US, révisée plutôt qu'appliquée

Le task file **interdisait** de poser `[MailboxNotRequired]` sur cette route :
*« on déplacerait le défaut du front vers le backend »*. task-313 l'a fait quand
même. **La consigne était juste, et la mesure lui a donné raison** —
`SessionsClosed = 0` est exactement le défaut déplacé.

Mais task-313 répondait à un problème réel : sans l'attribut, le praticien qui
détachait sa dernière messagerie voyait une **erreur 403 pendant une déconnexion
volontaire**, sans chemin de retour vers le rattachement.

**Les deux exigences se concilient, et c'est cette US qui les concilie.** Une
fois la fermeture déplacée en amont, la session utile est fermée à un instant où
l'adresse est résolue ; ce qui reste ensuite est une déconnexion d'un compte
sans aucune messagerie — il n'y a rien à fermer, et l'attribut ne fait qu'éviter
un refus inutile. **Il reste donc en place**, et le critère du DOD qui exigeait
son absence a été inversé.

#### Le piège que la US avait anticipé

`switchTo` ferme **lui-même** la session sortante. L'appeler après coup
rejouerait la clôture sur une boîte désormais détachée — le défaut corrigé, une
seconde fois et en silence. D'où un drapeau explicite plutôt qu'une seconde
implémentation de la bascule : `outgoingAlreadyClosed` sur les trois fronts, et
`closeMailSession: false` pour la déconnexion mobile.

#### Les tests mesurent un ORDRE

Un test qui vérifierait seulement que les deux appels ont eu lieu passerait
**aussi sur le code défectueux**. D'où un journal d'appels côté Angular et
mobile, `Received.InOrder` côté Blazor. Tous vérifiés **ROUGE avant
correction**.

La moitié des tests écrits fige ce qui ne doit **pas** changer : détacher une
boîte non courante n'émet aucune fermeture, et la fermeture n'est émise qu'une
fois quand un repli existe.

#### Qualité

`/sonar` skippé — `api-mail` non touché, le diff est exclusivement front.

| Repo | Tests | Lint |
|---|---|---|
| `client-blazor` | 249 (+4) | — |
| `client-mobile` | 853 (+4) | « All files pass linting » |
| `client-angular` | `mss-lib` 371 (+4), `weda2` 2 573 | 0 erreur, 41 warnings — **baseline exacte** |

Coût du cycle : **20 min 46 s** mesurées, 5 builds, 7 suites.

**Boucle d'auto-amélioration** — `conventions/angular.md`, `jsdoc/require-jsdoc`
passe à **3 occurrences**. La fiche disait déjà « modifier une signature, c'est
modifier son JSDoc » ; la récidive la confirme. Détail nouveau consigné : un
paramètre objet exige un `@param` par **sous-propriété**
(`@param options.maPropriete`), `@param options` seul ne suffisant pas.

#### Limites assumées

- **Une suggestion non bloquante, Blazor** : `CloseCurrentSessionAsync` prend un
  `CancellationToken` qu'elle **n'utilise pas** — `CloseServerSessionAsync()`
  n'en accepte aucun. Paramètre inerte sur une méthode d'interface neuve. Non
  corrigée : `/review` ne modifie pas de code, et Sonar ne tourne pas sur
  `client-blazor`.
- **Un critère du DOD, partiellement tenu** : il exigeait que la déconnexion et
  la bascule ordinaire restent vertes « sans modification d'assertion ». Tenu
  **pour la bascule ordinaire** (`MailboxSessionServiceTests`,
  `MailboxSwitcherComponentTests` intacts). Des assertions ont été modifiées sur
  le chemin de **détachement** — mises à jour de signature, pas
  d'assouplissement.
- **Vérification visuelle non produite** : aucun template touché, et le harnais
  reste absent du poste.

---

### v1.10 — task-313 : détacher sa dernière messagerie déconnecte, sur les trois fronts (`client-blazor`, `client-mobile`, `api-mail`)

> Portage sur Blazor et mobile du correctif livré sur Angular par task-312,
> **plus** le défaut backend que ce portage a rendu visible.
> PRs : [api-mail #241](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/241),
> [client-blazor #77](https://github.com/codengine-technologies/HealthPlatform.Client/pull/77),
> [client-mobile #73](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/73).

#### Ce que l'US ferme

Le praticien qui détachait sa **dernière** messagerie restait connecté avec une
session portant une boîte qui n'existe plus. Chaque appel suivant était refusé —
**y compris celui qui sert à rattacher une nouvelle messagerie**. Le compte
n'avait plus aucun chemin de retour : ni messagerie, ni moyen d'en ajouter une.

La décision humaine du 2026-09-15 — **déconnexion complète** — n'est pas qu'une
préférence d'ergonomie. C'est ce qui débloque le compte **sans toucher à une
seule garde de sécurité** : sans boîte annoncée, le backend prend l'autre
branche de la sélection, ne trouve rien de sélectionnable, et rend l'issue « une
messagerie est requise » — la seule que les routes de rattachement laissent
**déjà** passer.

#### Quatre défauts, dont deux que le portage a révélés

**1. Aucune déconnexion quand il ne reste rien** (les deux fronts). Les écrans
naviguaient vers l'onboarding en laissant la session ouverte.

**2. La décision se prenait sur une liste PÉRIMÉE** (les deux fronts). Les écrans
rechargeaient **avant** de décider ; ce rechargement est refusé tant que la
session porte la boîte détachée, et il sort alors **sans toucher** à sa liste —
`Result.Error` côté Blazor, `false` côté mobile. La boîte retirée y figurait
donc toujours comme sélectionnable **et** par défaut : les écrans trouvaient un
repli **qui n'existe plus** et rebasculaient vers la messagerie qu'on venait de
supprimer. C'est la même cause que sur Angular, écrite deux fois.

**3. Blazor « récupérait » vers la boîte détachée.** Propre à ce front, et plus
grave : `Mss403Handler` intercepte le refus et tente une récupération
automatique — mais **ne lisait pas le résultat de sa relecture**. Elle concluait
sur la même liste périmée et rebasculait vers la boîte détachée. *Le handler
réinstallait lui-même la cause du refus qu'il devait réparer.* La récupération
n'est pas supprimée — c'est un confort réel quand une boîte perd son jeton en
cours de session : on lui interdit seulement de **conclure sur une liste qu'elle
n'a pas pu rafraîchir**.

**4. L'ordre de clôture était refusé quand il n'y avait plus de boîte**
(`api-mail`). `POST /api/v1/sync/logout` portait l'exigence de messagerie par
défaut, alors que sa portée est *(praticien, session cliente)* : il purge le
contexte de synchronisation et journalise une frontière de session, sans jamais
lire ni écrire une boîte. Les trois fronts émettent cet ordre au **début** de
leur déconnexion — une erreur s'affichait donc pendant une déconnexion
volontaire. Corrigé par `[MailboxNotRequired]`, exemption **étroite** : le test
l'atteste en vérifiant aussi son **absence** sur une route qui, elle, manipule
une boîte.

#### Ce qui n'a PAS été réinventé

Les deux fronts avaient déjà leur couture de déconnexion, et elles sont
réutilisées telles quelles : `ISessionExpirationHandler.HandleExpiredSession()`
sur Blazor (task-156, **idempotent par contrat**) et `LogoutService.run()` sur
mobile (task-285). Aucun mécanisme nouveau n'a été introduit — c'est ce qui
explique la taille du diff au regard de l'effet.

#### Test-first, et les deux tests qui protègent du sur-correctif

Tous les tests du défaut ont été **vérifiés ROUGE avant correction** (règle 1) :
2 sur l'écran Blazor, 1 sur `Mss403Handler`, 3 sur mobile, 1 sur api-mail.

Mais la moitié des tests écrits fige **ce qui ne doit pas changer** : un repli
**réel** existe ⇒ on bascule ; la boîte détachée n'est pas la courante ⇒ la
session n'est pas touchée. Ces deux-là passaient **déjà** contre l'ancienne
logique, et c'est précisément leur intérêt : sans eux, « déconnecter »
deviendrait la réponse à *tout* détachement de la boîte courante — une
régression plus large que le défaut corrigé.

`mailbox-management.page.ts` (mobile) n'avait **aucun spec** : l'US en apporte
un de cinq tests.

#### Deux risques levés par vérification, pas par impression

1. **Purge croisée entre praticiens ?** Non. Avec `[MailboxNotRequired]`,
   l'adresse du praticien est vide sur ce chemin — état **documenté et voulu**
   du middleware. `CleanupUserAsync` ne l'utilise que comme **clé de recherche**
   (`TryGetValue`, `HasActiveSessionsForEmail`, `GetStateAsync`) : une chaîne
   vide ne correspond à rien, l'appel devient un no-op, jamais un effacement de
   masse.

2. **Service `AddScoped` résolu depuis le provider racine (Blazor) ?** Sans
   risque nouveau : `ISessionExpirationHandler` a le même cycle de vie et le
   même mode de résolution que `IMailboxSessionService`, que `Mss403Handler`
   résout déjà ainsi.

#### Qualité

| Métrique | Baseline | Final |
|---|---|---|
| Quality Gate (new code) | OK | **OK** |
| New coverage | 84,8 % | **85,8 %** |
| New bugs / vulnérabilités | 0 / 0 | **0 / 0** |
| Coverage projet | 87,7 % | **87,8 %** |
| Bugs / Vulnérabilités / Smells | 0 / 0 / 228 | 0 / 0 / 228 |

**0 itération de nettoyage, et c'est une mesure** : requête ciblée sur les deux
seuls fichiers du diff api-mail — **0 issue ouverte**. Les 35 *new smells* du
projet sont antérieurs à la branche et ne portent sur aucun fichier touché.
Lint mobile : « All files pass linting » dès la baseline.

Tests : **4 476** (api-mail) + **245** (Blazor) + **837** (mobile), 0 échec.
Coût du cycle : **29 min 19 s** mesurées, 7 builds et 18 suites.

#### Limites assumées

- **Un point de conformité remonté, non bloquant** — `questions/task-313.md`.
  Cette route devient la **première** route `[MailboxNotRequired]` qui émet une
  trace d'audit ; l'adresse étant vide par conception sur ce chemin, la trace de
  clôture est **non attribuable**. Ce n'est pas une régression (avant, la
  requête était refusée et *aucune* trace n'était écrite), mais trancher entre
  « ne pas émettre » et « émettre sous une identité de repli (sub PSC / RPPS) »
  est une décision de conformité — et la seconde option toucherait
  `AuditService`, donc **toutes** les traces de la plateforme.
- **Le code d'erreur trompeur n'est pas corrigé** : une messagerie **détachée**
  est rapportée comme un conflit d'identité PSC alors qu'elle n'en a aucun. Ce
  libellé a égaré le diagnostic pendant plusieurs échanges le 2026-09-15. Il
  mérite sa propre US — le corriger ici mêlerait un changement de contrat à un
  correctif de comportement.
- **Vérification visuelle non produite.** Aucun template n'a été modifié, et le
  harnais reste absent du poste. La réserve est explicite : l'US ajoute une
  **injection** à la page mobile, et une injection fautive produit un écran
  blanc — ce qu'un test unitaire ne voit pas, puisqu'il fournit lui-même le
  service. Couvert par le plan de test manuel, pas par la mesure.
- **`client-angular` hors périmètre** : déjà livré par task-312, committé par
  l'humain sur TFS.

---

### v1.9 — task-309 : le sélecteur de messagerie est monté, découvrable et couvert (`client-angular`, `client-mobile`, `client-blazor`)

**Statut** : `done` — PR [Client#76](https://github.com/codengine-technologies/HealthPlatform.Client/pull/76) et [Mobile#72](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/72), label **`awaiting-human-merge`** ; `client-angular` en **code-only** (10 fichiers non commités sur `feature/nova-rewriting-mss`)
**Branche** : `fix/task-309-selecteur-messageries-atteignable`
**Tests** : **+23** — `nx test mss-lib` **361 verts** (45 fichiers), mobile **832 verts**, Blazor **240 verts / 2 ignorés / 0 échec**
**Migration** : aucune
**Contrat** : **inchangé** — aucune PR `dtos-mss` (branche auto-incluse restée vide)

#### Ce que l'US ferme

task-304 a livré `mailbox-switcher` sur les trois fronts et ne l'a branché que sur deux.
Côté Angular, le composant était **écrit, exporté par `libs/mss/src/ui/index.ts`, et
monté nulle part** : `grep -rn "mss-mailbox-switcher" libs/mss/src --include=*.html`
ne rendait **aucun** montage. Le seul chemin vers `/messagerie/accounts` était de saisir
l'URL à la main.

Aucune suite n'a bronché, et c'est le fait intéressant : **un composant que rien
n'instancie ne casse rien**. Les trois sélecteurs n'avaient, par ailleurs, aucun test —
sur aucun front.

Le défaut est devenu bloquant avec task-308 : le rattachement étant devenu le **seul**
chemin d'obtention d'une boîte, le parcours s'arrêtait après la première.

#### Ce qui a été écrit

| Repo | Fichier | Apport |
|---|---|---|
| `client-angular` | `features/mail/mss-mail.component.{html,scss,ts}` | **L'en-tête de la page Messagerie**, qui n'existait pas, et le montage de `<mss-mailbox-switcher />` |
| `client-angular` | `features/layout/mss-layout.component.ts` | Entrée `NAV_ITEMS` `accounts` / `communication` / `mail-02`, **avant-dernière** |
| `client-angular` | `ui/mailbox-switcher/*` | Conversion design system (`ds-button`, `ds-card`, `ds-icon`) — `data-testid` **inchangés** — et `addMailbox()` |
| `client-angular` | 3 `*.spec.ts` (nouveaux) | 14 tests dont la contre-épreuve de montage |
| `client-mobile` | `mailbox/switcher/mailbox-switcher.component.{ts,html}` | `addMailbox()` + sa liaison |
| `client-mobile` | 2 `*.spec.ts` (nouveaux) | 9 tests dont la contre-épreuve de montage |
| `client-blazor` | `Plugin/Components/MailboxSwitcher.razor` | `AddMailbox()` |
| `client-blazor` | 2 `*Tests.cs` (nouveaux) | 8 tests bUnit dont la contre-épreuve de montage |

**La coquille était le vrai obstacle côté Angular.** `mss-mail.component.html` était un
`folder-panel` + un `content-panel` et rien d'autre, sans surface d'en-tête — là où
`Mail.razor:50` et `inbox.page.html:120` en avaient une. Il n'y avait littéralement nulle
part où poser le sélecteur. La page devient `.mail-shell` (colonne) = `.mail-header`
(`flex: 0 0 auto`) + `.mail-container` (`flex: 1 1 auto` + **`min-height: 0`**, sans quoi
un enfant flex refuse de descendre sous sa hauteur de contenu et la liste déborde au lieu
de défiler).

**Un échec de build instructif** : `justify="start"` sur `ds-button` — `ButtonJustify`
n'admet que `center | space-between` (`libs/design-system/src/atoms/button/button.types.ts:41`).

#### Le défaut trouvé par le test, et sa généralisation aux trois fronts

Le test « hors ligne, "Ajouter" ne navigue pas » a échoué **au premier coup** côté
Angular : un clic dispatché sur l'hôte `ds-button` **désactivé** déclenchait quand même
le `(click)` du parent. `ButtonComponent.handleClick` appelle pourtant
`stopImmediatePropagation()` quand `isDisabled()` — mais l'écouteur de template du
parent est enregistré **avant** l'écouteur d'hôte de la directive, donc il a déjà tiré.

**Ce n'est pas un bug utilisateur démontré** : le `<button disabled>` interne remplit
l'hôte et n'émet pas de clic ; il faudrait un chemin atteignant l'hôte (padding, clavier,
programmatique). Mais l'inopérance ne tenait qu'au **rendu**, alors que « rattacher exige
une session PSC » est une règle de l'écran. Une méthode la porte désormais sur les trois
fronts — `addMailbox()` / `AddMailbox()` — ce qui la rend vraie quel que soit le chemin du
clic **et vérifiable par un test**, comme l'exige la DOD santé de la task. « Gérer »
reste ouvert hors ligne.

#### Trois contre-épreuves, deux techniques

La question est la même partout — *la page monte-t-elle le sélecteur ?* — mais l'outil
décide de la réponse :

| Front | Technique | Pourquoi |
|---|---|---|
| Angular (Vitest/node) | lecture de `mss-mail.component.html` + de la liste `imports` | `readFileSync` disponible ; le compilateur couvre l'autre moitié (un élément inconnu casse le build AOT) |
| Blazor (xUnit) | lecture de `Mail.razor` via `RepoScan.RepoRoot()` | idem, et rendre `Mail.razor` exigerait session de boîte + dossiers + flux d'évènements |
| Mobile (Karma/navigateur) | **rendu superficiel** de `InboxPage` avec `NO_ERRORS_SCHEMA` | pas d'accès fichier dans le navigateur ; le schéma laisse la balise dans le DOM sans instancier la liste de mails |

#### Écarts de parité relevés

1. **Garde hors ligne absente des trois fronts** — *corrigée*, une méthode par front.
2. **Destination après bascule — non corrigée, arbitrage PO.** Angular route vers
   `[prefix, 'dashboard']`, Blazor vers `/Mail`, Mobile vers `/tabs/messages`. Le
   commentaire du code Angular annonce pourtant « la nouvelle boîte s'ouvre sur sa boîte
   de réception » : **le code et son commentaire divergent sur le front de référence**.
   Un mot suffit à aligner ; lequel des deux comportements est le bon est une décision
   produit.

Le reste est idiomatique et non un écart : menu ancré (Angular/Blazor) contre feuille
`ion-modal` (Mobile), et l'entrée de navigation « Mes messageries » **Angular seulement**
(les deux autres fronts n'ont pas de barre latérale).

#### Qualité

- **`/sonar` skippé** — `api-mail` non touché.
- **`/lint-angular` : 0 erreur dès la ligne de base**, 0 itération consommée sur 5.
  11 projets lintés (`nx affected -t lint --base=origin/next --head=HEAD
  --projects=tag:scope:mss`, `origin/next` à `c1f0ad90`) ; 56 avertissements, **tous
  préexistants** (`max-lines`, `jsdoc/require-example`, deux `complexity`). Le seul
  fichier du diff qui y figure, `mss-mail.component.ts`, y est pour `max-lines` à 675 —
  la task lui ajoute **deux** lignes.
- **`/lint-mobile` : `All files pass linting.`**, 0 erreur / 0 avertissement, 0 itération.
- **Aucune entrée à incrémenter dans `conventions/angular.md`** : le protocole ne se
  déclenche que sur une correction **manuelle**, et il n'y en a eu aucune. Le JSDoc de
  `addMailbox()` a été écrit avec la méthode — la règle qui avait coûté 23 squelettes
  creux à task-304 et deux `require-param` à task-308.
- **`/verify-visual` skippé** — diff mobile non visuel : deux specs, une méthode, une
  liaison de clic. Rendu identique au caractère près.

#### Passe qualité (`/simplify`)

Un seul nettoyage : la spec Angular contenait un test qui **réinitialisait le `TestBed`
en son milieu** pour exercer deux boutons — scindé en deux tests (d'où 361 et non 360).
Build applicatif non rejoué pour ce seul nettoyage, les specs étant hors bundle.

#### Limites assumées

- **`aria-expanded` a changé de porteur (Angular).** Il était sur le `<button>` natif ; il
  est désormais sur l'hôte `ds-button`, donc **pas sur l'élément focusable**. Corriger
  proprement demande une entrée `ariaExpanded` côté design system — hors module MSS.
- **`mss-mail.component.ts` dépasse `max-lines`** (675 / 500), avertissement préexistant
  aggravé de deux lignes. Le découper est un refactor à part entière.
- **Deux critères de la DOD restent des observations à l'œil** : la distinction des
  icônes `mail` / `mail-02` **en sidebar repliée**, et le fait que l'en-tête ajouté ne
  mange pas la hauteur utile de la liste sur un écran 1080p. Le test « les deux icônes
  diffèrent » est automatisé ; « elles se distinguent à l'œil » ne l'est pas.
- **`client-angular` reste code-only** : 10 fichiers non commités sur
  `feature/nova-rewriting-mss`. ⚠️ Les deux `apps/*/src/environments/environment.ts`
  modifiés dans le même arbre **préexistaient** à la task.

---

### v1.8 — task-311 : le seeder du banc provisionne le registre (`api-mail`)

**Statut** : `done` — PR [Api.Mail#240](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/240), label **`awaiting-human-merge`**
**Branche** : `fix/task-311-seeder-provisionne-registre`
**Tests** : **4 512 / 0 échec imputable** — dont **7 unitaires** (`LoadTestRegistryProvisionerTests`) et **5 d'intégration** contre un vrai PostgreSQL (`LoadTestBenchProvisioningIntegrationTests`). 5 échecs pré-existants (`…Today…` / `…NotSeenToday…` sur IMAP), reproduits à l'identique sur `develop` nu, travail remisé
**Migration** : aucune
**Contrat** : **inchangé** — aucune PR `dtos-mss` (branche auto-incluse restée vide)

#### Ce que l'US ferme

task-308 a supprimé `TenantRegistrySynchronizer.EnsureCurrentTenantAsync`, qui fabriquait
un rattachement à chaque requête authentifiée depuis le claim `mssEmail`. **C'est ce
mécanisme qui provisionnait le banc de charge à son insu** : le harnais k6 n'a jamais su
que le registre existait, ses boîtes se rattachaient toutes seules à la première requête.

Séquence avec un registre vide :

```
1. EnsureAccountAsync          -> la ligne `accounts` est creee, le compte existe
2. ApplyMailboxSelectionAsync  -> Client-Email = boite demandee
   -> GetMailboxAsync          -> aucun rattachement -> NotAttached
3. refus AVANT le controleur   -> 403 MAILBOX_NOT_ATTACHED
```

**Toutes les routes de messagerie répondaient 4xx** — y compris le `POST /api/v1/settings`
de l'étape 3 du seed lui-même. Il n'y avait plus rien à mesurer.

Second défaut, plus insidieux : `userContext.TenantId` ne vient plus que de la boîte
résolue (`UserContextEnricherMiddleware.cs:660`). Ce refus franchi, il serait resté nul et
`AuditService` serait retombé sur la base praticien — le mode dégradé prévu par task-300.
Le banc aurait donc cessé d'exercer le **journal mutualisé**, c'est-à-dire précisément
l'organe que task-300 a construit pour corriger 52 088 des 53 456 exceptions
« too many clients ». Un tir « vert » aurait mesuré autre chose que ce qu'on croit.

#### La voie écartée, et pourquoi

Faire appeler `POST /api/v1/account/mailboxes` par le seeder est **impossible** : le
domaine `loadtest.local` n'existe pas dans `MailServers.Domains`, donc la sonde
d'onboarding appelle `GetImapServerConfig(email)` **sans** configuration utilisateur, rend
`null`, et rien n'est rattaché. L'IMAP du banc fonctionne malgré cette absence parce que
`ImapConnectionService` passe `userSettings?.ImapServerConfig` en second argument —
court-circuit `FromUserConfig` dont la sonde d'onboarding, elle, ne dispose pas.

Ajouter `loadtest.local` à la table des domaines aurait fait entrer une configuration de
banc dans la configuration produit, et payé mille sondes IMAP au provisionnement.

#### Le correctif

Nouvelle **étape 0** du seeder, avant toute injection : pour chaque praticien synthétique,
les deux lignes que l'onboarding écrirait.

| Table | Colonne | Valeur |
|---|---|---|
| `accounts` | `authentication_subject` | le `PscSub` (ce que `TestBypassAuthenticationHandler` pose en `ClaimTypes.NameIdentifier` depuis `Client-Psc-Sub`) |
| | `email`, `username` | `loadtest-{n}@loadtest.local` |
| `mss_accounts` | `mailbox_address` | `loadtest-{n}@loadtest.local` |
| | `database_name` | `UserContextInfo.ProposeDatabaseName(email, rpps)` → `u_{rpps}_{slug}_{hash}` |
| | `is_default` | `true` |
| | `validated_by_psc_subject` / `validated_by_rpps` | le `PscSub` / le `Rpps` du praticien |

**L'écriture passe par le câblage de la production**, pas par du SQL de banc :
`AddTenantRegistryClient` + `ITenantRegistryClient.EnsureAccountAsync` /
`AttachMailboxAsync` — le chemin d'écriture de l'onboarding moins la sonde XOAUTH2. Un
`INSERT` maison aurait ré-implémenté en silence la normalisation d'adresse, le choix de la
boîte par défaut, l'ancrage PSC et l'unicité « un RPPS = un compte ».

**Les identités ne sont jamais recalculées** : elles viennent de `LoadTestPlanGenerator`
(`Rpps => $"9{Index:D10}"`, `PscSub => $"00000000-0000-4000-8000-{Index:D12}"`), la source
que `tests/loadtest-k6/lib/identity.js` reproduit côté k6. Un écart d'un caractère et la
règle 4 de `MailboxCompatibility` refuse la session en `PscIdentityConflict` — un tir
intégralement rouge, pour une raison invisible dans les rapports.

#### Fichiers

| Fichier | Rôle |
|---|---|
| `tests/mss.mail.testing.shared/LoadTestRegistryProvisioner.cs` | La logique, partagée par le seeder **et** les suites de tests |
| `tests/mss.mail.loadtest.seed/RegistryComposition.cs` | Composition DI : câblage de production + mise à niveau du schéma |
| `tests/mss.mail.loadtest.seed/Program.cs` | Étape 0 et son échec bruyant |
| `tests/mss.mail.loadtest.seed/SeedOptions.cs` | `--registry` + variable `TenantRegistry__ConnectionString` |
| `src/Infrastructure/Extensions/ServiceCollectionExtensions.cs` | `AddTenantRegistryClient` publique et **étroite** ; `AddTenantRegistry` redevient privée et s'appuie dessus |
| `src/Infrastructure/Migrations/TenantDb/TenantRegistryBootstrap.cs` | **Nouveau** — définition unique de « la base commune est prête » |
| `src/Infrastructure/Migrations/TenantDb/TenantRegistrySchemaInitializer.cs` | Réduit à l'appel du bootstrap |
| `tests/mss.mail.integration.tests/Fixtures/TenantRegistryTestClient.cs` | **Nouveau** — `ContextFactory` + `AlwaysMissCache` dédupliqués de **4 copies** à une |
| `docs/loadtest.md` | Étape 0 documentée, avec les requêtes psql de contrôle |

#### Le défaut trouvé par la passe qualité

`RegistryComposition` ne rejouait que la **migration** du registre ;
`TenantRegistrySchemaInitializer`, lui, enchaîne migration **puis**
`AuditPartitionMaintenance.EnsurePartitions`. Un seed lancé avant le premier démarrage
d'api-mail — un cas normal du banc, et la raison même de migrer dans l'outil — obtenait
donc un schéma à jour **sans partitions**, et les traces du tir seraient tombées dans la
partition `DEFAULT`. Dans l'organe que cette US existe pour faire exercer.

`TenantRegistryBootstrap.Ensure` porte désormais la définition unique de l'état « prêt » ;
le service hébergé et l'outillage l'appellent tous deux. **Vérifié empiriquement** :

```
select count(*) from pg_class where relname like 'audit_traces%' and relkind in ('r','p');
-> 6   (la table partitionnee + 5 partitions d'avance)   AVEC le correctif
-> 1   (la table seule, tout en DEFAULT)                 SANS
```

#### Garde-fous

- **Idempotent** — le balayage d'entrée sert trois fois : garde d'environnement, sonde de
  joignabilité, et **inventaire de ce qui est déjà rattaché**. Un re-seed de 1 000
  praticiens ne repaie plus ~10 000 allers-retours pour finir sur autant d'exceptions de
  conflit attrapées.
- **Bruyant** — `ListTenantsAsync` est l'une des rares lectures du contrat qui **propagent**
  la panne ; les lectures du chemin de requête dégradent en « je ne sais pas », ce qui
  rendrait un registre injoignable indistinguable d'un registre vide. Le seed s'arrête
  **avant** la demi-heure d'injection.
- **Borné au banc** — refus d'un domaine **routable** (suffixes réservés RFC 2606 / 6761 :
  `.local`, `.localhost`, `.test`, `.invalid`, `.example`) et refus d'un registre portant
  déjà un compte non synthétique. Le refus nomme le **domaine**, jamais l'adresse : une
  adresse MSSanté est une donnée à caractère personnel, y compris dans un message d'erreur.

#### Vérification en conditions réelles

Seeder exécuté contre le PostgreSQL du banc, registre neuf :

```
1er passage : Registre provisionne : 3 praticien(s) (3 cree(s), 0 deja present(s))
2e passage  : Registre provisionne : 3 praticien(s) (0 cree(s), 3 deja present(s))
```

Lignes contrôlées en base : `authentication_subject` = `PscSub`,
`database_name` = `u_90000000001_l1l_dfdfa3be…`, `validated_by_rpps` = `90000000001`,
`is_default = t`. Base de test supprimée après coup.

#### Sonar

**Aucune dette introduite** : zéro finding sur les fichiers de la task, vérifié par
filtrage des 181 violations du *new code period* par composant **et** par dates de création
des issues ouvertes (2025-12-28 → 2026-09-14, aucune datée du jour). Le Quality Gate est
`ERROR` parce que la *new code period* inclut les tasks E016 déjà mergées (15 issues du
11/09, 11 du 13/09, 18 du 14/09) — piège connu de ce projet.

L'écart `code_smells` 72 → 253 et la note de sécurité A → E viennent du **périmètre
analysé** : cette analyse a couvert `tests/loadtest-k6/**` (24 `.py`, 24 `.js`, 2 `.ps1`)
que la précédente n'avait pas indexé. Les deux « vulnérabilités » sont le littéral
`PGPASSWORD=postgres` d'`observe.ps1` — l'identifiant synthétique du Postgres de banc
local, le même que le défaut `MSS_BENCH_PG_PASSWORD` de l'AppHost. **Aucun secret réel.**

#### Limites assumées

- **Le test de l'US monte une sonde, pas `MailController`.** Il assemble le vrai chemin
  d'identité — bypass de test, `UserContextEnricherMiddleware`, résolution de boîte contre
  un vrai registre PostgreSQL — devant un point terminal qui rend `userContext.TenantId`.
  Le refus corrigé est émis **par le middleware, avant le contrôleur** : monter Dovecot et
  une base praticien pour observer un refus qui ne les atteint jamais n'aurait rien prouvé
  de plus, et aurait rendu la preuve tributaire d'IMAP.
- **Le paramétrage de `PGPASSWORD` dans `observe.ps1`** (4 occurrences, dont 2 signalées)
  est reporté à une task dédiée : script PowerShell non couvert par les tests, hors module
  de cette US, et ce cycle n'aurait pas pu vérifier le correctif.
- **`RegistryComposition.Build` résout un service `scoped` depuis le fournisseur racine.**
  Correct aujourd'hui (`BuildServiceProvider()` n'active pas `ValidateScopes`) et vérifié à
  l'exécution ; une portée explicite serait plus robuste si la validation était activée.
- **Cette US ne tire pas.** Elle rend le banc exploitable. La campagne qui suivra devra
  **ré-établir une référence** : les tirs antérieurs à task-300 ne sont plus comparables.
### v1.7 — task-312 : le journal d'audit hérité est retiré, et la purge de rétention branchée (`api-mail`)

**Statut** : `done` — PR [Api.Mail#239](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/239), label **`awaiting-human-merge`**
**Branche** : `chore/task-312-retrait-audit-herite`
**Tests** : **3 960 / 0 échec** sur le périmètre de la task ; 5 rouges pré-existants hors diff (`…Today…`, corpus IMAP daté relativement au jour du semis) — **vérifiés identiques sur `origin/develop` nu**, worktree détaché, même poste, même minute
**Migration** : `20260915090000_DropAuditCutoverMarks` (TenantDb, **neuve** — règle 7c) + édition de `20240101_SetupMigration` (MailDb, **mergée** — écart assumé, cf. ci-dessous)
**Contrat** : **inchangé** — aucune PR `dtos-mss` ; la branche auto-incluse est restée vide
**Sonar** : Quality Gate new code **OK**, new coverage 83,0 → **84,8 %**, new smells 40 → **35**, projet 0 bug / 0 vulnérabilité / 233 → **228** smells, ratings **A / A / A**

#### Ce que l'US ferme

task-300 avait mutualisé le journal d'audit en base commune et prévu une **lecture double
source** transitoire : au-delà de `mss_accounts.audit_cutover_at` on lisait `audit_traces`,
en deçà la table `MssAuditTraces` de la base praticien. task-301 devait reprendre
l'historique puis la faire cesser, tenant par tenant.

**Cette transition n'a jamais eu lieu.** La reprise était écrite et mergée, mais elle ne
s'est jamais exécutée sur un parc réel — et l'application n'est pas en service. Arbitrage
humain du 2026-09-14 : **il n'y a aucune donnée de production à reprendre**, donc l'état
final se atteint par **suppression** plutôt que par migration.

#### Ce qui part

| Pièce | Rôle |
|---|---|
| Table `MssAuditTraces` + 4 index | le magasin hérité, **une table par praticien** |
| `AuditTraceRepository`, `IAuditTraceRepository`, son `DbSet` | son accès |
| `AuditBackfillService`, `IAuditBackfillService`, `IAuditBackfillStore`, `PostgresAuditBackfillStore`, `AuditBackfillHostedService`, `AuditBackfillOptions`, `AuditBackfillReport` | la machinerie de reprise entière |
| Fusion double source de `PostgresAuditReader` (`ReadLegacyAsync`, `ReadTenantMarksAsync`, `MergeWindowCap`, `CloneWithWindow`) | la lecture transitoire |
| `audit_cutover_at`, `audit_backfilled_at` | ses deux bornes |
| `Audit:DrainParallelism`, `Audit:DrainMaxConnections` | deux réglages sans objet — ils bornaient le nombre de **bases praticien** drainées en même temps ; il n'y en a plus qu'une |
| `docs/runbook-reprise-audit.md` | le mode opératoire d'une opération qui n'existe plus |

Le chiffre qui justifiait la mutualisation reste le même : une table d'audit **par
praticien** faisait s'étaler un lot de 100 traces sur ~100 bases, ~100 pools Npgsql et
~100 logins Postgres — **52 088 des 53 456** exceptions « too many clients » mesurées le
2026-09-08, soit **97 %**.

#### Trois choses que seul le retrait pouvait révéler

**1. `IAuditJournalPurge` n'avait aucun appelant.** Il était enregistré en DI depuis
task-300, et personne ne l'invoquait : la **seule** purge qui s'exécutait réellement était
celle du drain, sur la table héritée. Et elle était *opportuniste* — déclenchée par
l'activité du tenant lui-même, donc **jamais** pour un praticien ayant cessé d'utiliser le
produit. Retirer la table sans brancher la purge mutualisée aurait laissé un journal
porteur d'INS, de nom de patient, de sujet et d'expéditeur croître **sans effacement à
échéance** (RGPD art. 5.1.e) : on aurait remplacé une dette technique par un manquement.

`AuditRetentionHostedService` est donc créé dans cette US, et c'est le **premier item de
son DOD**. Il balaie le journal entier sans connaître les tenants — ce qu'une table unique
rend enfin possible. Partitions d'abord (`DropPartitionsOlderThanAsync`, le chemin bon
marché), lots par famille ensuite. Cadence par **marqueur Redis à TTL** (`SET NX`, dont
l'expiration *est* le limiteur de débit) : deux réplicas ne peuvent pas lancer la passe
ensemble, et aucune comparaison d'horloge n'est nécessaire. **Sans Redis, pas de purge** —
le journal grossit, ce qui est la direction sûre : mieux vaut conserver trop que supprimer
deux fois.

**2. `TransportAttempts` ne s'incrémentait plus.** Son unique point d'incrément vivait dans
la persistance trace-à-trace de la base praticien, retirée ici. Sans le geste, le compteur
serait resté à `0`, le budget poison (`MaxPersistAttempts`) jamais atteint, et une trace
qu'aucune insertion ne peut accepter — contrainte violée, colonne trop longue — serait
revenue au tampon **indéfiniment**. Réinstallé dans `ParkFailedTraceAsync`, le point unique
où passe désormais toute trace en échec.

**3. Le tri de l'écran d'audit avait cessé d'exister.** Sonar l'a signalé sous la forme
« paramètre `sortBy` inutilisé » (S1172) — c'était le **symptôme**, pas le défaut. La
**seule** implémentation qui honorait le tri était celle de la base praticien ; le chemin
mutualisé ordonnait toujours par horodatage décroissant. Tant que les deux sources
coexistaient, le paramètre gardait un effet. En retirant la source héritée sans rapatrier
le tri, l'API aurait continué d'**accepter** `sortBy` en l'**ignorant** : des en-têtes de
colonne cliquables qui ne trient plus rien, **sans la moindre erreur**.

`PostgresAuditReader.ApplySort` reprend **à l'identique** les six champs triables et le
défaut de `AuditTraceRepository.ApplyAuditSort` — un retrait ne change pas un comportement
en passant. Couvert par `AuditReaderSortIntegrationTests` (4 cas, **base dédiée** : les
traces tombent en partition `DEFAULT`, et le fichier voisin compte à la fois les partitions
et les lignes de `DEFAULT`).

#### Les traces sans tenant — le fail-fast et son arbitrage

`/develop` s'est **arrêté** sur `questions/task-312.md` : le dépôt hérité n'était pas
seulement un vestige, c'était le **chemin d'écriture nominal** des traces sans `TenantId`.
Elles existent par nature — un échec d'authentification survient avant toute résolution de
boîte.

La question posée n'était pas technique : router ces traces sous un tenant sentinelle les
rend invisibles dans l'écran d'audit de tout praticien (la RLS filtre sur `tenant_id`), et
rendre invisible un évènement de sécurité qui concerne le praticien est une décision de PO
et de conformité.

L'humain a d'abord demandé **« quel évènement devient invisible exactement ? »** — ce qui a
corrigé une surestimation de l'analyse : seul **`MailboxAttached` au tout premier
rattachement** est systématiquement sans tenant. `MailboxDetached` en porte un dès lors
qu'il reste une boîte. Après cette précision : arbitrage **A + B**.

- **Volet A — estampillage à la source.** `MailboxAttached`, `MailboxDetached` et
  `MailboxDefaultChanged` portent désormais le tenant **concerné**. Le middleware posait
  celui de la boîte *courante* : au premier rattachement il n'y en a aucune, et aux
  suivants il désigne **une autre boîte** que celle qu'on vient de rattacher. Dans les deux
  cas la trace mentait sur son objet.
- **Volet B — tenant sentinelle `Guid.Empty`** pour le résiduel. `Guid.Empty` n'appartient
  à personne. **Aucune visibilité existante n'est retirée** : le dépôt hérité filtrait sur
  `UserId == email`, et une trace émise avant toute résolution de boîte ne porte pas
  l'email du praticien — ces traces n'étaient déjà visibles de personne.

#### Écarts assumés

| Écart | Motif |
|---|---|
| **Édition d'une migration mergée** (`20240101_SetupMigration`, règle 7c) | Décision humaine du 2026-09-14. Aucune donnée de production, et une base neuve ne doit pas créer une table qu'on supprimerait à la migration suivante. Le bloc supprimé est remplacé par un commentaire qui dit ce qui vivait là et pourquoi |
| **Aucun `Delete.Table`** ajouté | Une base de développement **existante** garde sa table `MssAuditTraces` orpheline. Sans conséquence : elle n'est plus ni lue ni écrite |
| **46 fichiers** (repère règle 5 : ~30) | 15 sont des **suppressions**. L'arbitrage humain (« tout faire d'un coup ») a écarté le découpage : un retrait à moitié ne compile pas, donc ne se merge pas |
| **Phase 2 Sonar non exécutée** | Les 34 findings restants sont tous dans des fichiers que l'US ne touche pas (`ITenantRegistryClient` ×14 `CA1068`, `BaseRepository`, `TenantRegistryExceptions`). Le seul `CRITICAL` restant est **S3776**, blacklisté, traité par `/sonar-s3776` |
| **5 tests rouges** | `…Today…` ×5, pré-existants — vérifiés identiques sur `origin/develop`. Méritent leur propre task |

#### Tests : adaptés quand l'invariant survit, supprimés quand le sujet disparaît

| Fichier | Sort | Motif |
|---|---|---|
| `AuditBackgroundServiceBatchingTests` | **adapté** | Mesure toujours « combien d'écritures pour N traces ». L'assertion « deux groupes » s'**inverse** en « un seul lot » — c'était la forme même du défaut corrigé par task-300 |
| `AuditBackgroundServiceFallbackTests` | **adapté** | Tampon, budget poison, charge utile : invariants task-292, intacts. Les deux tests de concurrence par groupe praticien partent avec leur sujet |
| `AuditBackgroundServiceReplayAndPurgeTests` | **scindé** → `…ReplayTests` | La purge n'est plus une branche du drain ; ses tests suivent la purge dans `AuditRetentionHostedServiceTests` |
| `AuditDirectRouteIntegrationTests` | **supprimé** | Tout le fichier portait sur la route directe vers la table héritée |
| `CrossTenantOwnershipTests` (section audit) | **supprimé** | L'isolation ne se joue plus en C# (`UserId == email`) mais en **RLS Postgres**. `AuditJournalIntegrationTests` la vérifie là où elle s'applique — avec un cas de plus que l'ancien couple ne savait pas voir : **deux PS sur la même adresse organisationnelle** |
| `AuditRetentionHostedServiceTests` | **créé** | 7 cas : partitions avant lots, borne par famille, verrou légal sur les **deux** chemins, passe à vide muette, `SET NX` et marqueur pris, absence de Redis, puits en panne |
| `AuditReaderSortIntegrationTests` | **créé** | 4 cas sur la régression de tri ci-dessus |

#### Trouvé par la revue

Trois **commentaires orphelins** laissés par le retrait — un commentaire de section sans
ligne en dessous, un commentaire `task-301` devenu l'en-tête d'un enregistrement DI sans
rapport, une ligne vide double. Corrigés (`35586b9`). Un commentaire qui survit au code
qu'il décrit désigne la mauvaise ligne.

#### Outillage : le port de SonarQube a encore changé

`agents/sonar.md` affirmait « 9001 ». Mesuré ce jour : `docker port sonarqube` rend
`9000/tcp -> 0.0.0.0:9000`, et 9001 ne répond pas. **Troisième correction en six
semaines.** L'encadré a été réécrit pour ne plus graver *aucune* valeur — seulement la
procédure de contrôle et `$SONAR_HOST_URL`.

#### Coût du cycle

| Étape | Statut | Durée |
|---|---|---|
| `/start` | ok | 24 s |
| `/develop` | ok | 15 builds, 2 suites |
| `/sonar` | ok (2 itérations) | 19 min 27 s |
| `/lint-angular`, `/lint-mobile`, `/verify-visual` | skipped | — |
| `/review` | ok | 4 min 17 s |
| **Total** | | **24 min 11 s** — 21 builds (1 min 47 s), 13 suites (11 min 07 s) |

---

### v1.6 — task-308 : le registre sépare ses deux identités (`api-mail`, `client-blazor`, `client-mobile`, `client-angular`)

**Statut** : `done` — PR [Api.Mail#238](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/238), [Client#75](https://github.com/codengine-technologies/HealthPlatform.Client/pull/75) et [Mobile#71](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/71), label **`awaiting-human-merge`** ; `client-angular` en **code-only** (l'humain pousse sur TFS)
**Branche** : `feat/task-308-registre-deux-identites`
**Tests** : **5 902 / 0 échec** — 4 500 (api-mail) + 232 (Blazor) + 823 (mobile) + 347 (Angular mss-lib)
**Migration** : `20260914180000_SplitKeycloakAndPscIdentities`
**Contrat** : **inchangé** — aucune PR `dtos-mss`, `MailboxDto` n'a pas bougé

#### Ce que l'US ferme

task-303 avait fait de la boîte une **sélection validée par le registre**, et task-304
l'avait rendue visible. Restait un trou que personne n'avait vu : **le registre se
remplissait tout seul**, avant que le front n'ait pu poser la question.

Constaté le 2026-09-14 sur une première connexion réelle via Keycloak + proxy + PSC : le
praticien n'a **jamais vu l'onboarding**. Sa messagerie s'est ouverte directement.

#### La mesure, à la milliseconde

```
16:34:43.395  accounts.created_at         <- EnsureAccountAsync        (compte Keycloak seul, correct)
16:34:43.691  mss_accounts.attached_at    <- EnsureCurrentTenantAsync  <- LE rattachement automatique
16:34:43.801  [LegacyClaims] Compte migre <- n'a fait que l'ANCRAGE du compte
```

Le coupable apparent était `LegacyClaimsMigration`, le chemin de transition de task-303.
**Ce n'était pas lui.** La preuve est un `NULL` : `EnsureTenantAsync` pose
`validated_by_psc_subject` *à la création* du rattachement, et la ligne produite ne le
portait pas. Elle avait donc été créée par un chemin **sans identité PSC** — le
synchroniseur, 110 ms plus tôt, depuis le seul claim `mssEmail`.

Supprimer la migration des claims seule n'aurait rien changé.

#### Deux coupes, indissociables

**1. Un seul écrivain.** `TenantRegistrySynchronizer` ne crée plus aucun rattachement. Il
enregistre le compte, horodate, et s'arrête là. Rattacher une messagerie redevient un acte
unique et explicite — `POST /api/v1/account/mailboxes` — précédé d'une **sonde XOAUTH2**
que l'opérateur MSSanté valide. `LegacyClaimsMigration` disparaît avec lui, ainsi que
`EnsureTenantAsync`, `EnsureTenantRequest` et `AnchorPscIdentityAsync`, devenus sans
appelant : laisser une opération capable de rattacher hors du chemin validé, c'est laisser
en place la faute qu'on vient de retirer.

**2. Deux identités, deux tables.**

| Table | Avant | Après |
|---|---|---|
| `accounts` | `sub` + `rpps` + `psc_subject` + horodatages | `sub` + **`email`** + **`username`** + horodatages — la **projection du user Keycloak**, et rien d'autre |
| `mss_accounts` | `validated_by_psc_subject` (nullable) | `validated_by_psc_subject` **et `validated_by_rpps`**, tous deux **`NOT NULL`** |

Le principe : `accounts` répond à « quel compte Keycloak ? », `mss_accounts` à « quelle
messagerie, validée par quel professionnel ? ». **Aucune ligne ne mélange plus les deux
autorités.** Keycloak authentifie ; PSC et l'opérateur MSSanté disent qui est le
professionnel, et ils ne le disent qu'au rattachement.

`email` et `username` sont **dénormalisés et non autoritaires** : ils rendent une ligne du
registre lisible par un humain sans aller-retour vers Keycloak. La clé reste
`authentication_subject` — l'email est mutable et son unicité dépend d'un réglage de realm.
Un commentaire de colonne en base grave l'interdit : *ne jamais joindre `accounts.email` à
`mss_accounts`*, sous peine de réintroduire la conflation « 1 compte = 1 boîte ».

#### L'ancrage devient dérivé — et le détachement ne le défait pas

`accounts.psc_subject` portait l'ancrage et la règle « pas de re-binding silencieux »
(task-049, règle 3). Sans cette colonne, l'ancrage se **dérive** des rattachements :
*toutes les boîtes d'un compte partagent la même identité PSC.*

La dérivation lit **tous** les rattachements, **détachés compris**. Sans cela, détacher sa
dernière boîte suffirait à rendre le compte réattribuable à un autre professionnel — par
une opération que le praticien déclenche lui-même. La règle anti-ré-association serait
contournable en deux clics.

Effet de bord favorable : la règle 2 de `MailboxCompatibility` **gagne** en portée. Elle
comparait un rattachement à une colonne qu'on écrivait soi-même ; elle compare désormais
les rattachements **entre eux**, et détecte un compte dont deux boîtes auraient été
validées par des professionnels différents.

#### Le cross-check PSC/KC est retiré — c'était forcé

`ApplyPscKcCrossCheckAsync` (task-048) comparait `(mssSub, mssRpps)` du jeton Keycloak à
`(sub, SubjectNameID)` du jeton PSC. Son étape 1 exige la **complétude des trois claims**.
Ces claims ayant disparu du realm, et `appsettings.json` portant `"Enforce": true`, il
aurait répondu **403 à toute requête authentifiée**.

Sa garantie est reprise — et **renforcée** — par `MailboxCompatibility` règle 4 : l'identité
PSC de la session doit concorder avec l'ancrage du compte, lequel vient d'une sonde XOAUTH2
validée par l'opérateur. Les claims, eux, étaient auto-déclarés par le jeton même qu'on
cherchait à vérifier. `PscIdentityOptions` part avec le mécanisme qu'il gouvernait.

#### Ce que « un RPPS = un compte » est devenu

L'index unique partiel `ix_accounts_rpps` part avec sa colonne, et **aucun index ne peut le
remplacer** : un praticien à N boîtes produit N lignes au même `validated_by_rpps`. La
garantie descend au niveau applicatif, dans `AttachMailboxAsync`, et un test la couvre —
deux `authentication_subject` distincts ne peuvent pas rattacher sous le même RPPS. Un
index **non unique** (`ix_mss_accounts_validated_by_rpps`) en supporte la requête, sans
quoi chaque rattachement balaierait toute la table.

#### Côté fronts : aucun comportement, seulement la preuve

L'audit des trois fronts a montré que la table de décision « 0 boîte → onboarding » était
déjà implémentée **et testée** partout, et qu'aucun ne lisait plus les claims retirés. Le
seul maillon non couvert était la **redirection** elle-même : `mailbox.guard.ts` n'avait de
spec ni sur Angular ni sur Mobile, et le `switch` de `Mail.razor` n'était testé nulle part —
seuls les écrans d'arrivée l'étaient, rendus directement.

Ce trou devient inacceptable ici : l'onboarding étant désormais le **seul** moyen d'obtenir
une boîte, une garde qui cesse de rediriger ne laisse plus le praticien devant un mauvais
écran — elle le laisse devant une messagerie vide, sans chemin pour en rattacher une.
Quatre tests par front, dont la contre-épreuve qu'une boîte ouverte n'en déclenche aucune.
**Le diff front ne contient que des fichiers de test.**

#### Trois défauts trouvés pendant la revue de code

| Trouvaille | Correctif |
|---|---|
| `AttachMailboxAsync` filtrait sur `validated_by_rpps` **sans index** | `ix_mss_accounts_validated_by_rpps`, déclaré dans la migration **et** dans le `DbContext` |
| Deux flux SSE répondaient « JWT lacks the mssEmail claim » là où il manque une **messagerie ouverte** — un praticien en onboarding y tombe légitimement | Messages corrigés, comportement inchangé |
| `RegistryMeter` devenu un champ privé inutilisé (S1144) | Classe et `AddMeter` supprimés — un meter exporté sans instrument ne remonte rien en le faisant croire |

#### Qualité

**Quality Gate OK.** Code smells 233 → **231**, couverture 87,3 % → **87,4 %**, couverture
*new code* **83,5 %** (seuil 80), ratings **A / A / A**, 0 bug, 0 vulnérabilité. 1 itération.
Les 37 findings restants du new-code sont acceptés : 30 `external_roslyn` en INFO, 6 sur du
code pré-existant hors diff, 1 `S3776` en liste noire.

#### Réserves consignées

- **`LoadAnchorAsync` sur le chemin chaud** — une requête indexée de plus par requête
  authentifiée, rendant au plus une ligne. À mesurer au banc avant la prochaine campagne de
  capacité. C'est la seule ligne du diff qui mérite un chiffre.
- **48 fichiers** dans la PR `api-mail`, au-delà du repère « ~30 » de la règle 5.
  Indivisible : `validated_by_rpps NOT NULL` ne tient que si le synchroniseur a cessé de
  fabriquer des lignes sans PSC.
- **Le banc de charge devra rattacher explicitement.** Ses boîtes étaient créées par le
  synchroniseur ; `TestBypassAuthenticationHandler` émet encore les trois claims, désormais
  morts. À traiter dans le harnais.
- **La purge est assumée et non réversible.** Les rattachements sans
  `validated_by_psc_subject` sont supprimés par la migration — décision humaine du
  2026-09-14, l'application n'étant pas en production. Les praticiens concernés repassent par
  l'onboarding, une fois. Le `Down()` recrée le schéma, jamais les données : une migration
  qui prétendrait restaurer ce qu'elle a supprimé mentirait sur ce qu'elle garantit.

#### Ce qui devient possible après ce merge

Le retrait des mappers Keycloak `mssEmail` / `mssSub` / `mssRpps` et de la route
`PUT /v1/admin/mss-profile` du proxy (`psc-auth-proxy`, hors automation de la forge) n'a plus
aucun effet de bord côté `api-mail`. Action humaine.

---

### v1.5 — task-304 : la sélection devient visible (`client-blazor`, `client-angular`, `client-mobile`)

**Statut** : `done` — PR [Client#74](https://github.com/codengine-technologies/HealthPlatform.Client/pull/74) et [Mobile#70](https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/70), label **`awaiting-human-merge`** ; `client-angular` en **code-only** (l'humain pousse sur TFS)
**Branche** : `feat/task-304-selection-et-bascule-de-boite`
**Tests** : **3 962 / 0 échec** — 228 (Blazor) + 2 915 (Angular : weda2+mss+mss-lib) + 819 (mobile)
**Paquet consommé** : `HealthPlatform.Dtos.Mss` **474.0.0** (publié par task-303 ; `client-blazor` bumpé depuis 454.0.0)

#### Ce que l'US ferme

task-303 avait rendu la boîte **sélectionnable** côté serveur. Rien ne le montrait :
pour le médecin, rien n'avait changé. C'est exactement ce que la règle 11 appelle de
la plomberie, et c'est pourquoi ses PRs portaient `awaiting-us-completion`.

task-304 est la moitié visible. Elle retire des trois fronts le dernier endroit où
« un compte = une boîte » était encore gravé : **la lecture du claim**.

#### Le claim disparaît des trois fronts

| Front | Avant | Après |
|---|---|---|
| `client-blazor` | `AuthService.ExtractMssEmailFromJwt` → `UserSessionService.UserEmail` → en-tête `Client-Email` | `MailboxSessionService` tient la boîte ouverte ; `AccountService` la lit. `AuthService` n'établit plus que l'**identité** (nom, RPPS) |
| `client-angular` | `mssHeadersInterceptor` lisait `jwtDecoded.mssEmail` et `jwtDecoded.sid` | l'intercepteur lit `MailboxSessionStore` ; `IJsonWebTokenPayload.mssEmail` **retiré du type** |
| `client-mobile` | `sessionFromTokenAggregate` dérivait `mssEmail` ; `needsMssOnboarding` en décidait l'onboarding | la session ne porte plus que `practitionerName` / `rpps` ; `mailboxGuard` interroge le **registre** |

`Client-Session-Id` cesse par ailleurs d'être la claim `sid` côté Angular : c'est un
identifiant **applicatif**, tiré au login et rotaté à chaque bascule — comme le mobile
le faisait déjà depuis task-282.

#### La table de décision à sept états

Deux entrées seulement — la session porte-t-elle un jeton PSC, et combien de boîtes
sélectionnables — et un écran par issue. Elle est implémentée **une fois par front**,
et couverte **par un test par cas et par front** : c'est une table de décision, pas
une liste d'exemples.

Le cas **1** est le cas neuf : compte Keycloak authentifié, zéro boîte, pas de jeton
PSC. Jusqu'ici le claim garantissait qu'une session authentifiée avait toujours une
boîte ; ce n'est plus vrai. Ce n'est ni une erreur ni un blocage — c'est l'état normal
d'un compte qui n'a pas encore joué l'onboarding, et l'écran `mailbox-psc-required`
l'explique sans afficher la moindre erreur technique, **sans aucun formulaire** (la
sonde XOAUTH2 ne peut pas aboutir sans jeton PSC : offrir un champ ne mènerait qu'à un
échec après saisie).

Le cas **6** porte l'exigence hors ligne, et son arbitrage mérite d'être consigné.
La question posée le 2026-09-13 était : hors ligne avec un défaut, faut-il afficher
l'écran de sélection ? Il rendrait la lecture seule visible **avant** toute tentative
d'écriture, là où l'ouverture directe laisse le praticien découvrir la dégradation en
cliquant sur « Répondre ». **La fluidité l'a emporté** — et la conséquence est non
négociable : le bandeau « Hors ligne — lecture locale » est **présent au premier
rendu**, persistant, au-dessus de la liste, jamais un toast ; les commandes d'écriture
sont grisées **et visibles** dès l'ouverture.

#### La bascule est une fin de session, pas un changement d'en-tête

```
gel + annulation des requêtes en vol + fermeture SSE
  → POST /sync/logout AVEC LES EN-TÊTES DE LA SESSION SORTANTE
    → purge totale de l'état
      → NOUVEL identifiant de session + nouvelle boîte
        → réabonnement SSE ?mailbox= + chargement
```

Chaque étape rend la suivante sûre. Annuler avant de fermer évite qu'une réponse de la
boîte sortante peuple l'interface de l'entrante ; fermer **avec les anciens en-têtes**
est la seule façon pour le backend de savoir quelle session fermer ; purger avant de
tirer le nouvel identifiant garantit qu'aucun écran ne se peint avec un état mixte.
Exécuter ces étapes dans un autre ordre ne dégrade pas la bascule, **elle la casse** —
d'où un test d'**ordre** par front, qui échoue si une étape bouge ou disparaît.

La rotation de l'identifiant n'est pas une hygiène. Le backend lie un
`Client-Session-Id` à la première boîte qu'il a ouverte et refuse en 409
`SESSION_MAILBOX_MISMATCH` le même identifiant présenté avec une autre : c'est ce qui
empêche une bascule de laisser un pool IMAP orphelin. Un 409 reçu **après** une bascule
est donc un défaut de front — journalisé en **erreur**, jamais avalé.

#### La purge est énumérée, pas écrite en dur

Le point qui décide si « rien de la boîte sortante ne survit » reste vrai dans six
mois. Les trois fronts exposent une **liste de porteurs d'état** résolue depuis le
conteneur — `IMailboxScopedState` (Blazor), `MSS_RESETTABLE_STORES` (Angular),
`MAILBOX_SCOPED_STATES` (mobile) — que la bascule réinitialise tous sans en connaître
un seul. Un service ajouté plus tard qui oublie de s'y inscrire est le mode d'échec
attendu, et il est explicite.

Côté mobile, la liste est **vide et documentée** : l'état de boîte y vit dans les
pages, détruites par la navigation qui suit chaque bascule. Le tableau vide n'est pas
un oubli — c'est ce qui rend l'ajout d'un futur service racine explicite.

#### La clôture est partagée avec la déconnexion

`closeMailboxSession()` est **extraite** de `LogoutService` (mobile) et
`SyncProgressService.LogoutCleanupAsync` **réutilisée** (Blazor) plutôt que
réimplémentées. Une boîte quittée se ferme toujours de la même façon, qu'on se
déconnecte ou qu'on change de messagerie. En écrire une seconde version aurait garanti
qu'elles divergent.

Un échec de cette clôture est journalisé et **ne bloque pas** la bascule : le serveur a
son propre filet d'expiration, et emprisonner le praticien sur l'ancienne boîte serait
le pire des deux maux.

#### Les erreurs en cours de session deviennent une reprise

`Mss403Handler` cessait d'expliquer et se met à **reprendre**. Une boîte détachée
depuis un autre poste, ou qui cesse de correspondre à l'identité PSC pendant que le
praticien travaille, déclenche un rechargement de la liste puis une bascule vers le
défaut compatible — pas un message sur un état que le praticien n'a pas provoqué.

#### Deux constats portés au HAG

**1. Lacune du contrat task-303.** `AttachMailbox` rend `Problem(409, …)` pour « déjà
rattachée » **et** pour « identité non concordante », **sans code machine** — alors que
les 403 d'appartenance portent le leur dans `instance`. Les trois fronts ne peuvent pas
les distinguer autrement qu'en lisant le message, ce que la règle 12 proscrit. Ils
affichent donc le `detail` du serveur tel quel plutôt que de deviner. Le correctif est
d'une ligne côté `api-mail`, hors `**Repos**:` de cette task (règle 6) ; **la PR #236
de task-303 est encore ouverte** et c'est l'endroit naturel pour le poser.

**2. `Tools/visual-verify/` absent du poste.** Le harnais de capture Playwright n'est
pas versionné — `.gitignore` exclut `Tools/` en bloc et ne réintroduit que
`Tools/timing/`. Les quatre critères « Outillage visuel » de la DOD restent donc non
satisfaits, et `Docs/epics/img/screens/client-mobile/mss-setup.png` /
`mss-unconfigured.png` documentent désormais des écrans **supprimés**. Le premier geste
au retour du harnais n'est pas une capture mais la fixture `mailboxes.json` : le mock
rend `[]` sur tout `GET` non mappé, donc sans elle **toute la galerie mobile
deviendrait l'écran d'onboarding**. Détail et options : `questions/task-304.md`.

#### Qualité

- `/sonar` **skippé** — `api-mail` non touché.
- `/lint-angular` : **57 → 0 erreur** en 2 itérations. L'auto-fixer a corrigé 55
  `prettier/prettier` mais inséré **23 squelettes JSDoc vides** — il satisfait la règle
  sans rien documenter. Repris à la main, et gravé dans `conventions/angular.md` :
  écrire le JSDoc en même temps que la méthode, ne jamais s'en remettre à `--fix`.
- `/lint-mobile` : **« All files pass linting »** dès la baseline, 0 itération.
- Revue de code : **APPROVED**, avec deux fragilités corrigées au passage — un
  `First()` qui levait si l'invariant de la table de décision évoluait, et un verrou
  `_opening` jamais relâché qui laissait « Ouvrir » grisé après un échec.

**Coût du cycle mesuré** : 1 h 14 min — 26 builds (3 min 52 s), 23 suites (3 min 54 s).

---

### v1.4 — task-303 : la boîte MSSanté devient une sélection (`api-mail`, `dtos-mss`)

**Statut** : `done` — PR [Api.Mail#236](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/236) et [Dtos.Mss#32](https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/32), label **`awaiting-us-completion`** (règle 11 — vague 1/2)
**Branche** : `feat/task-303-comptes-multi-messageries` (2 repos, les deux avec commits)
**Commits** : 11 — dont un merge d'intégration de task-300
**Tests** : **4 519 / 0 échec** (16 ignorés), dont **71 nouveaux**
**Paquet** : `HealthPlatform.Dtos.Mss` **474.0.0**

#### Ce que l'US ferme

Avant elle, la boîte MSSanté d'un praticien était un **claim signé par Keycloak** :
un utilisateur Keycloak, une boîte, une base. Changer de boîte exigeait un nouveau
jeton, donc une déconnexion — et l'onboarding était orchestré par le client
(sonder, puis demander l'écriture d'un attribut, puis « reconnectez-vous »).

task-303 remplace ce claim par une **sélection validée à chaque requête** contre le
registre livré par task-299 **et** contre l'identité PSC de la session.

Le fondement est vérifié dans le code, pas supposé : l'authentification IMAP/SMTP
se fait en **XOAUTH2 avec le jeton PSC**, et ce jeton identifie le
**professionnel** (RPPS en `SubjectNameID`), jamais une boîte. Un même jeton ouvre
donc légitimement toute boîte que l'**opérateur MSSanté** a rattachée à ce PS.

#### Le modèle de données passe à deux tables

`tenants` absorbe `mailboxes` et devient **`mss_accounts`**. Trois raisons, toutes
vérifiées dans le schéma livré par task-299 :

1. **Double clé de fait** — la table portait à la fois `mailbox_id` et la copie
   dénormalisée `mailbox_address`, les deux indexées par compte. Une adresse
   corrigée d'un côté laissait l'autre périmée, en silence.
2. **L'entité intermédiaire ne portait rien** — `RegistryMailbox` n'était rendu par
   aucune opération du contrat, et `operator_domain` se dérive de l'adresse.
3. **Elle rendait possible une faute qu'on se contentait de documenter** — trois
   paragraphes avertissaient de ne jamais clé le journal d'audit sur `mailbox_id`,
   sous peine de faire voir à deux praticiens d'une adresse organisationnelle les
   traces l'un de l'autre. **Supprimer la colonne rend la faute impossible.**

Ce qu'on abandonne, et c'est assumé : l'identité globale d'une adresse partagée.
Deux praticiens sur `secretariat@…` donnent deux lignes, deux bases, **aucun parent
commun sur lequel se tromper**.

#### La règle métier centrale : deux questions, deux réponses

`MailboxCompatibility` répond séparément à « **cette boîte est-elle utilisable ?** »
(`selectable`) et « **cette session peut-elle ouvrir IMAP ?** » (`capabilities`).

Les confondre — ce que faisait la première rédaction de l'US — rangeait
« pas de jeton PSC » parmi les incompatibilités et rendait, composé avec la règle
d'affichage du front, **toutes les boîtes inaccessibles hors ligne** : l'inverse
exact du comportement voulu, puisque le hors ligne existe précisément pour lire ce
qui est déjà synchronisé. La règle est pure, sans I/O, et couverte par une
**matrice de 14 tests**.

#### Ce qui empêche la bascule de casser le parc existant

`LegacyClaimsMigration` est le **seul** lecteur restant de `mssEmail` / `mssSub` /
`mssRpps`. Sans elle, la bascule mettrait **tout le parc** en 403 au premier appel :
le registre connaîtrait leur compte mais aucune de leurs boîtes. Elle ancre le
compte et rattache sa boîte par défaut en une opération idempotente, et le nom de
base proposé est **exactement celui que le praticien utilisait déjà** — il ne change
pas de base en migrant.

Classe isolée, marquée `[Obsolete]`, avec le compteur qui autorisera son retrait :
`mss_registry_legacy_claims_migrations_total` à zéro pendant 30 jours.

#### Trois défauts trouvés en écrivant les tests

1. **La course perdue rendait un `TenantId` inexistant en base** — prérequis hérité
   de la revue de task-299. La première correction était **elle-même fausse** : elle
   relisait par `account.Id`, or quand c'est l'insertion du *compte* qui perd la
   course, cet identifiant n'a jamais été écrit. La relecture repart du **sujet
   d'authentification**. Le test tirait un sujet fixe : il a échoué au premier
   passage puis **réussi au second**, la base de test conservant l'état — il tire
   désormais un sujet neuf à chaque exécution, et la course a été rejouée trois fois.

2. **Trois lecteurs de `mssEmail` subsistaient**, trouvés par un test de garde ajouté
   pour ça (lecture des sources). Le plus grave : `BiologyAckService` serait retombé
   sur `ClaimTypes.Email` et aurait imputé l'acquittement d'un résultat de biologie
   au **compte technique Keycloak** au lieu du praticien — une erreur d'imputabilité
   dans un journal de données de santé, pas un détail d'affichage.

3. **Un bug `S2583`** (fiabilité tombée à C) sur une condition que l'analyseur lisait
   comme toujours fausse. Il avait tort sur le fond, mais une condition qu'un outil
   lit de travers est une condition qu'un relecteur lira de travers : forme explicite.

#### La garde de session n'est pas de l'hygiène de contrat

Un `Client-Session-Id` est lié à la **première boîte qu'il ouvre** ; le présenter
avec une autre rend **409 `SESSION_MAILBOX_MISMATCH`**. Le registre des sessions IMAP
étant clé sur `{email}_{sessionId}`, réutiliser un identifiant ne provoque **aucune
collision** — il **abandonne** la session précédente, laissant un pool IMAP+SMTP
orphelin, toujours connecté chez l'opérateur d'avant. Dix bascules, dix pools
résidents : exactement la classe de fuite que l'EPIC de capacité E015 a passé six
semaines à corriger. Le multi-onglets reste légitime ; un identifiant ne se recycle
pas, même après un `/sync/logout`.

#### Intégration avec task-300, mergée pendant le développement

Conflit **sémantique**, pas textuel — task-300 a ajouté `audit_cutover_at` à la table
que cette US renomme :

- **Ordre des migrations** : celle de task-303 portait un identifiant *antérieur* à
  celui du journal d'audit, qui fait `ALTER TABLE tenants`. Sur une base **neuve**,
  la table aurait déjà été renommée et **le service n'aurait pas démarré** — défaut
  invisible sur les bases de développement déjà migrées. La règle 7c interdisant
  d'éditer une migration mergée, c'est celle de task-303, encore sur sa branche, qui
  a été renumérotée.
- **`PostgresAuditSink`** visait `tenants` en SQL brut : aligné sur `mss_accounts`.
  C'est le seul SQL brut du produit qui nommait cette table.
- **`TenantId` recalé sur la boîte retenue** : le synchroniseur pose le tenant de la
  boîte héritée ; il est désormais recalé sur la boîte effectivement ouverte. Sans ce
  recalage, les traces d'un praticien qui bascule seraient classées sous sa boîte
  d'ouverture — et le journal mutualisé, **dont le `TenantId` est la seule
  frontière**, mélangerait deux messageries.

#### Qualité

| Métrique | Avant | Après |
|---|---|---|
| Bugs / Vulnérabilités | 0 / 0 | **0 / 0** (1 introduit, corrigé) |
| Fiabilité / Sécurité / Maintenabilité | A / A / A | **A / A / A** |
| Code smells (code neuf) | — | 48 → **41** |
| Couverture | 88,6 % | 87,3 % (neuf : 81,5 %) |

**Quality Gate ERROR** sur `new_security_hotspots_reviewed` : quatre points chauds,
tous **LOW**, tous du motif « vérifier que la configuration du logger est sûre », et
**aucun dans un fichier créé par cette US**. Leur revue est un acte de sécurité
humain — la forge ne les marque pas « revus » à la place de l'humain.

#### Écarts assumés

- **Provisionnement de la base au rattachement** : reste **paresseux** (première
  requête sur la boîte), mécanisme existant et éprouvé.
- **Tests d'intégration HTTP par endpoint** : la logique est couverte au niveau
  service, ordre sonde → persistance compris (`Received.InOrder`).
- **Banc de charge** : extrait en **task-306**. ⚠️ Cette US livre ce dont il dépend —
  le sujet d'authentification sur le chemin de contournement. **À partir d'ici, le
  banc écrit dans le registre et paie ses lectures : la référence de capacité E015 se
  déplace, et c'est cette US qui la déplace**, pas task-299 qui était neutre.

---

### v1.3 — task-301 : reprise de l'historique d'audit (`api-mail`)

**Statut** : `done` — PR [Api.Mail#235](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/235), label `awaiting-human-merge`
**Branche** : `feat/task-301-reprise-historique-audit` (2 repos ; `dtos-mss` auto-inclus, **0 commit**)
**Commits** : 4 — **22 fichiers**
**Tests** : **4 463 / 0 échec** (16 ignorés), dont **10 dédiés à la reprise**

#### Ce que l'US ferme

task-300 a déplacé les traces **nouvelles** vers la base commune. Celles déjà écrites dans
les mille bases praticien y restaient, et le chemin de lecture double — commune au-delà de
la bascule, praticien en deçà — devait vivre indéfiniment.

task-301 recopie l'existant, **le vérifie**, puis fait cesser la lecture double **tenant par
tenant**.

#### La contrainte qui gouverne tout

> Une reprise qui prend une nuit est un succès. Une reprise qui sature le serveur est un
> échec, même plus rapide.

Le 2026-09-11, une opération large sur le parc — le rejeu du tampon d'audit — a ouvert
**2 500 backends en trois minutes**, produit **27 575 refus `53300`** et figé la VM Docker
**45 minutes**, trois fois dans la même journée. La reprise fait la même chose en pire :
elle touche *toutes* les bases, délibérément.

| Borne | Valeur | Ce qui la vérifie |
|---|---|---|
| Concurrence | 4 bases simultanées | test observant la concurrence **réelle** sur 40 tenants |
| Lots | 1 000 traces, curseur sur `Id` | — |
| Saturation | pause au-delà de 600 connexions | fixture simulant la saturation |
| Reprenable | tenant marqué ⇒ ignoré **sans lecture** | rejeu ⇒ 0 insertion |

**Chacune se perd sans que rien n'échoue** : une reprise sans plafond marche parfaitement
sur trois tenants de test, et met le serveur à genoux sur mille.

#### L'ordre des opérations est le cœur de la correction

`compter → copier → **vérifier** → marquer`.

Marquer avant de vérifier ferait cesser la lecture héritée pour un tenant dont la copie est
peut-être incomplète : **le praticien perdrait une partie de son historique sans qu'aucune
erreur ne soit levée.** Un comptage divergent échoue bruyamment, le tenant reste non marqué,
et rien n'est supprimé.

Un tenant en échec **n'interrompt jamais les autres** : sur mille bases, une reprise qui
s'arrête au premier incident n'arrive jamais au bout.

#### Le verrou de suppression a été déplacé du runbook vers le code

Trouvé pendant `/review`. La DOD demande que la suppression de la table héritée soit
« appliquée **uniquement** aux tenants marqués repris et vérifiés ». Le mécanisme existait,
mais la garde vivait dans la **documentation**.

Sur une opération **irréversible** portant sur une source de traçabilité PGSSI-S, ce n'est
pas suffisant : `DropLegacyTableAsync` prend désormais le **tenant** — et non le seul nom de
base — pour relire `audit_backfilled_at` et **refuser** si la marque est absente.

> Une garde qui n'existe que dans un document finit un jour par être contournée depuis une
> console, sur le mauvais tenant, à deux heures du matin.

#### Déclencheur : configuration, jamais route HTTP

`api-mail` n'a pas d'ordonnanceur, et le task file exclut le cron. Une route serait le
déclencheur naturel — mais **il n'existe aucun modèle de rôles** dans ce service
(`questions/task-302.md`). Exposer derrière une route non habilitée une opération qui lit
l'intégralité du journal d'audit du parc ouvrirait un chemin d'exfiltration pour gagner une
commodité d'exploitation.

`Backfill:RunOnStartup` + redémarrage d'**un seul** réplica. Le jour où task-302 livre un
modèle de rôles, une route pourra s'y substituer sans rien changer au service.

#### Écart assumé — la configuration « morte » ne l'est pas encore

La DOD demandait de supprimer `Audit:DrainParallelism` et le plafond de drain. **Non fait**,
et c'est raisonné : task-300 a gardé l'ancien chemin comme **filet** pour les traces sans
`TenantId` (registre désactivé ou injoignable), filet accepté à son merge. Les retirer ne
supprimerait aucune architecture parallèle mais rendrait ce chemin **non bornable** — soit
exactement le défaut que task-298 contient.

La DOD pose elle-même la condition : « tant que le chemin hérité vit, le réglage doit rester
réglable ». **Il vit.** Le retrait est rattaché à la suppression des tables héritées : même
déclencheur — parc entièrement repris — et même nature, on ne retire un filet qu'une fois
certain de ne plus en avoir besoin.

#### Tests dédiés (10)

`AuditBackfillServiceTests` (7 unitaires : concurrence observée, déjà-repris ignoré sans
lecture, idempotence, pause de saturation, échec isolé, comptage divergent bruyant, hygiène
des journaux) — `AuditDualSourceReadTests` (+1 : contenu **identique** avant/après reprise) —
`AuditJournalIntegrationTests` (+1 bloquant : verrou de suppression dans les deux sens) —
plus le test de bascule par tenant.

#### Sonar — 2 itérations, **0 issue sur le code neuf**

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| `new_violations` | 167 – 170 | 168 | ≈ 0 |
| `new_code_smells` | 166 | 164 | −2 |
| Quality Gate | ERROR | ERROR | = |

3 issues attribuables corrigées (`S138` — trois lignes d'enregistrement poussaient
`AddApplication` de 97 à 100 lignes ; `CA1822` ; `xUnit2033`). `S4457` appliqué **sans que
Sonar le signale**, par respect de la convention dont le compteur venait d'être incrémenté.

> **Note de méthode** : l'API `measures` et l'API `issues` de SonarQube rendent des chiffres
> différents par décalage d'indexation (170 vs 167 en fin de task-300). **Le compte d'issues
> ouvertes fait foi.** Vérifié ici : une `CA1822` listée juste après le scan avait disparu
> d'une requête faite une minute plus tard.

**Documentation** : runbook `Api/Mail/docs/runbook-reprise-audit.md` — lancer, suivre,
reprendre après incident, et surtout **vérifier avant de supprimer**.

---


### v1.2 — task-300 : journal d'audit en base commune (`api-mail`)

**Statut** : `done` — PR [Api.Mail#234](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/234), label `awaiting-human-merge`
**Branche** : `feat/task-300-journal-audit-base-commune` (2 repos ; `dtos-mss` auto-inclus, **0 commit**, pas de PR)
**Commits** : 6 — **35 fichiers, +3 364 / −28 lignes**
**Tests** : **4 456 / 0 échec** (16 ignorés), dont **21 dédiés au journal mutualisé**

#### Le défaut corrigé, et pourquoi c'était un défaut de placement

Le journal était écrit dans une table **par praticien** — placement hérité du choix
« un médecin, une base », jamais décidé pour le journal. Un lot de 100 traces s'étalait
donc sur ~100 bases, ~100 pools Npgsql, ~100 logins Postgres : **52 088 des 53 456**
exceptions `53300` venaient de là, soit **97 %**. Le remède « évident » — drain
concurrent, degré 8 — avait **aggravé** (15 873 `08P01` contre 646).

Un journal d'audit est un flux append-only à fort débit, quasiment jamais relu : le
remède naturel est l'insertion groupée, et le sharding par tenant **détruit
mécaniquement la groupabilité**. On payait le coût maximal de l'isolation pour un
bénéfice d'isolation quasi nul.

#### Ce qui a été livré

| Brique | Chemin | Rôle |
|---|---|---|
| `audit_traces` | migration `Migrations/TenantDb/20260914090000` | Table partitionnée par mois, PK `(id, timestamp)`, index `(tenant_id, timestamp DESC)`, partition `DEFAULT` |
| `IAuditSink` / `IAuditReader` / `IAuditJournalPurge` | `Application/Services/Repository/TenantDb/` | Contrats — **hors du SDK**, même règle que le registre depuis la révision du 13/09 |
| `AuditTraceRecord` | `Domain/Entities/TenantDb/` | Ce qui franchit le contrat ; **aucun champ `Transport…`** (l'un portait un mot de passe Postgres) |
| `PostgresAuditSink` | `Infrastructure/Repositories/TenantDb/` | Un lot, une instruction, une connexion — `Application Name=mss-mail-audit`, pool **2** |
| `PostgresAuditReader` | idem | Lecture double source, confinée ici, supprimée par task-301 sans toucher une signature |
| `PostgresAuditJournalPurge` | idem | Purge par lots + suppression de partition, verrou légal prioritaire |
| `AuditPartitionMaintenance` | `Migrations/TenantDb/` | Avance de 3 mois maintenue au démarrage, verrou consultatif partagé |
| `tenants.audit_cutover_at` | migration | Borne de bascule **par tenant**, posée à l'horodatage de la première trace mutualisée |

#### Trois couches d'isolation, à la place d'une frontière de base

| Couche | Ce qu'elle tient |
|---|---|
| RLS PostgreSQL | `tenant_id = NULLIF(current_setting('mss.tenant_id', true), '')::uuid`, `FORCE ROW LEVEL SECURITY` |
| Deux rôles | `mss_audit_writer` (INSERT, **pas** SELECT) / `mss_audit_reader` (SELECT sous RLS, **pas** INSERT) |
| Filtre applicatif | optimisation de plan, **jamais** la sécurité |

#### Quatre défauts trouvés à l'implémentation — tous silencieux, tous prouvés à l'exécution

C'est la partie de cette entrée qui vaut d'être relue avant la prochaine US touchant
PostgreSQL. Aucun des quatre n'aurait échoué en test unitaire.

1. **`ON CONFLICT (id, timestamp) DO NOTHING` exige le privilège `SELECT`** — PostgreSQL
   doit inspecter l'index arbitre. Or le rôle d'écriture ne doit précisément pas pouvoir
   lire : il écrit pour **tous** les tenants, donc un `SELECT` ferait de lui un point
   d'exfiltration de tout le parc. La forme **sans cible d'inférence** ne demande aucun
   privilège de lecture et couvre la même contrainte.
2. **`current_setting(…, true)` rend une chaîne vide, pas `NULL`, sur une connexion
   recyclée.** Une fois un paramètre personnalisé posé dans une session — fût-ce par
   `SET LOCAL` —, il revient à chaîne vide, et le cast en `uuid` lève `22P02`. Sans
   `NULLIF`, la lecture suivante servie par le pool **échouerait** au lieu de rendre zéro
   ligne.
3. **`DELETE … WHERE ctid IN (…)` est FAUX sur une table partitionnée.** Le `ctid` est un
   emplacement physique, unique **par** partition et non entre partitions. L'idiome
   standard pour borner un `DELETE` supprimait donc des traces d'autres partitions,
   **encore dans leur durée de conservation**. Constaté : une trace du jour supprimée par
   une purge visant les traces de plus de 365 jours.
4. **`SET LOCAL` hors transaction explicite n'a aucun effet** au-delà de l'instruction :
   PostgreSQL crée une transaction implicite puis la valide. Au moment où la requête
   part, rôle **et** tenant ont été annulés. En production, l'écran d'audit du praticien
   aurait été **vide**. Masqué parce que l'utilisateur des conteneurs de test est
   `SUPERUSER` et **contourne la RLS**, y compris `FORCE ROW LEVEL SECURITY`.

> **Le quatrième a produit une leçon de méthode** : un test de sécurité qui tourne sous
> superutilisateur ne teste pas la sécurité. Le test qui l'a attrapé se connecte avec un
> rôle **ordinaire**, et la régression a été **ré-injectée** après correction pour
> vérifier qu'il mord — il échoue alors sur « Collection was empty », le symptôme exact
> de production.

#### Dépendance découverte : le tenant n'était jamais matérialisé

L'en-tête de l'US affirmait « Indépendante de task-303 : `TenantId` étant défini dans
task-299 ». **Faux.** task-299 a livré la table des tenants et `EnsureTenantAsync`, mais
**rien ne l'appelait** : `TenantRegistrySynchronizer` n'appelait qu'`EnsureAccountAsync`,
et la table était vide dans tous les environnements. Un journal clé sur `tenant_id`
n'avait aucun tenant à référencer.

Résolu ici au plus petit périmètre — boîte courante, nom de base déjà utilisé par
l'application. task-303 étend cette résolution à la sélection multi-boîtes ; elle ne la
refait pas.

#### Tests dédiés (21)

`AuditJournalIntegrationTests` (10, vrai PostgreSQL : RLS, rôles, partitions, purge,
idempotence, borne de bascule) — `AuditDualSourceReadTests` (3, dont **1 bloquant sous
utilisateur ordinaire**) — `AuditDrainMutualisationTests` (3, unitaires : un appel par
lot, repli sans tenant, invariant task-292) — `AuditJournalLogHygieneTests` (2, aucune
donnée de santé dans les journaux techniques) — `TenantRegistryContractTests` (+6 cas :
surface des trois contrats du journal).

#### Trois items de DOD comblés pendant `/review`

Cochés à blanc, ils auraient fait passer la PR pour complète : chaîne de connexion dédiée
`mss-mail-audit` (pool 2), test de lecture double source, test d'hygiène des journaux.

#### Sonar — 2 itérations, **0 issue sur le code neuf**

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| `new_violations` | 155 | 167 | +12 |
| Quality Gate | ERROR | ERROR | = |
| `new_coverage` | 89,1 % | 88,2 % | −0,9 |

Le `+12` vient de la **fenêtre de new-code**, pas du code neuf : toucher un fichier y fait
entrer ses issues **préexistantes**. Vérifié issue par issue — **0 sur les 14 fichiers
créés**, 0 imputable sur les fichiers modifiés. 3 issues corrigées (`S4457` ×2,
`xUnit2033`), dont une **récidive** : la consigne S4457 existait depuis task-299
(compteur 1 → 2).

#### Ce que cette US rend caduc

`Audit:DrainMaxConnections` et `Audit:DrainParallelism` n'ont plus d'objet **sur le chemin
d'audit**. **task-298 n'est pas annulée pour autant** : son `application_name` explicite
reste nécessaire quelle que soit l'architecture, et son plafond protège le chemin de
provisionnement.

#### Le risque assumé, à accepter au HAG

Le mode de panne devient **global** : la base commune indisponible contre-pressionne
**tous** les praticiens. Tampon Redis de 3 h, contre-pression en filet. Deux atténuations
livrées : les traces **sans tenant** gardent l'ancien chemin (un registre absent ne rend
pas le journal inopérant), et la partition `DEFAULT` absorbe tout horodatage hors plage.

**Documentation** : `ADR-2026-09-14-journal-audit-mutualise.md`, plus la réserve §4.y
ajoutée à `ADR-2026-07-27-pgbouncer-transaction-mode.md`.

---


### v1.1 — task-299 : registre des tenants (`api-mail`, + un `sdk` réduit à sa CI)

**Statut** : `done` — PR [Host.Sdk#3](https://github.com/codengine-technologies/HealthPlatform.Host.Sdk/pull/3) et [Api.Mail#233](https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/233), label `awaiting-human-merge`
**Branche** : `feat/task-299-registre-tenants` (3 repos ; `dtos-mss` auto-inclus, **0 commit**, pas de PR)
**NuGet publié** : `HealthPlatform.Host.Sdk 14.0.0` (run CI 14) — **référencé par personne** après la révision ci-dessous ; `api-mail` est revenu à `13.0.0`
**Commits** : `sdk` 3 - `api-mail` 8 - **~2 700 lignes ajoutées**
**Tests** : `sdk` **16/16** - `api-mail` **4 424 / 0 échec** (16 ignorés), dont **57 dédiés au registre** (dont **12 d'intégration sur vrai PostgreSQL**)

> **Révision du 13/09/2026, après `/review` et avant tout merge.** Le contrat du registre devait
> vivre dans le SDK pour préparer le futur service du réseau privé. Décision humaine : le coût réel
> était un **cycle de publication à chaque évolution du modèle** — commit SDK, attente de CI,
> publication NuGet, bump de consommateur — pour un modèle qui bougera à chaque vague de l'EPIC.
> Les types sont rapatriés dans `api-mail`, isolés par espace de noms. `Sdk/TenantRegistry/` est
> supprimé ; PR #3 ne porte plus que le déclencheur CI (`branches: [ "**" ]`), utile au cycle de
> la forge.
>
> **Ordre de merge : plus d'objet.** `api-mail` ne compile plus contre un paquet dont le code
> source serait absent de `develop` du SDK. Les deux PRs sont indépendantes.

#### Le défaut de conformité corrigé

`AuditRetentionOptions.PurgeInterval` l'admettait noir sur blanc : « no way to enumerate the
practitioner databases, so a global nightly job would have nothing to iterate over ». La purge
de rétention étant **opportuniste**, déclenchée par l'activité du tenant lui-même, un praticien
qui cessait d'utiliser le produit **ne déclenchait plus jamais de purge** — ses traces, porteuses
de `PatientIns` et de `PatientName`, restaient au-delà de leur durée de conservation,
indéfiniment (RGPD art. 5.1.e).

#### Contrat du registre — isolé par espace de noms, plus par paquet

| Rôle | Types | Emplacement |
|---|---|---|
| Données franchissant le contrat | `RegistryAccount`, `RegistryMailbox`, `RegistryTenant`, `TenantState` | `Domain/Entities/TenantDb` |
| Contrat | `ITenantRegistryClient`, `EnsureTenantRequest` | `Application/Services/Repository/TenantDb` |
| Pannes typées | `TenantRegistryUnavailableException`, `TenantRegistryConflictException` | `Application/Exceptions` |

Symétriquement, les **22 entités du courrier** descendent de `mss.mail.Domain.Entities` à
`mss.mail.Domain.Entities.MailDb` — 310 fichiers, renommage mécanique. Les deux domaines sont
désormais des espaces **frères**, comme `Migrations/`, `Persistance/` et `Repositories/` depuis la
restructuration FluentMigrator.

Cinq contraintes de migrabilité, **toutes tenues par des tests** parce qu'elles sont toutes
silencieuses à la perte (`TenantRegistryContractTests`, 8 tests, portés depuis le dépôt SDK) :
`record` immuables (détection `init`-only via `IsExternalInit`), **aucune entité de persistance ne
franchit le contrat**, aucune séquence différée en retour, pannes typées avec le contrat,
`CancellationToken` + `correlationId` sur chaque opération. Deux tests sont **nés de la révision** :
`NoPersistenceType_CrossesTheContract` remplace la barrière d'assembly perdue (tant que le contrat
vivait dans un paquet, exposer un `RegistryTenantRow` était *impossible* ; c'est désormais une ligne
qui compile), et `TheContract_DoesNotDependOnTheSdk` épingle la décision — le SDK reste référencé
pour `IResilientCacheService`, donc une rechute passerait sans bruit. Les énumérations de types sont
assertées **non vides** — sans quoi les tests passeraient à vide.

Le **versionnement par espace de noms** (`.V1`) est abandonné : il protège un consommateur externe
déjà livré, et il n'y en a plus.

#### Implémentation `api-mail`

| Brique | Chemin | Rôle |
|---|---|---|
| `PostgresTenantRegistryClient` | `src/Infrastructure/Repositories/TenantDb/` | **Seule** implémentation ; cache-first + invalidation explicite, budget de temps (`CallTimeout` 3 s), dégradation par opération, traduction des pannes |
| `TenantRegistryDbContext` + les trois `…Row` | `src/Infrastructure/Persistance/TenantDb/` | Trois tables ; index unique **filtré** `WHERE rpps IS NOT NULL` ; unique partiel `WHERE is_default` (au plus une messagerie par défaut par compte, garanti par la base) |
| `CreateTenantRegistry` + `TenantRegistryMigrator` | `src/Infrastructure/Migrations/TenantDb/` | Migration FluentMigrator du registre et son coureur, **bornés par `TypeFilterOptions`** au seul espace `…Migrations.TenantDb` |
| `MigrationHelper` | `src/Infrastructure/Migrations/` | Création de base (`42P04` bénin) et **verrou consultatif partagé** par les deux bases — `SET LOCAL lock_timeout`, clé SHA-256 stable, budget client > budget serveur |
| `TenantRegistrySchemaInitializer` | `src/Infrastructure/Migrations/TenantDb/` | `IHostedService` ; un échec **ne bloque pas le démarrage** |
| `TenantRegistrySynchronizer` | `src/Application/Services/Implementation/` | Crochet du middleware ; bride horaire sur l'horodatage d'activité |
| `TenantRegistryOptions` | `src/Application/Configuration/` | Défauts dans le code, pas dans le JSON ; chaîne vide = registre désactivé ; chaîne câblée par l'`AppHost` (`MSS_TENANT_REGISTRY_DB`, défaut `mss_registry`) |

#### Trois écarts assumés par rapport au task file

1. **Crochet dans `UserContextEnricherMiddleware`, pas sur le chemin de provisionnement.**
   `BaseRepository.HandleEnvironmentDbSetupAsync` est conditionné à `Development`/`Staging`
   (ligne 540) : s'y accrocher n'aurait **jamais rien écrit en Production**.
2. **Nommage `TenantRegistry`.** `DirectoryController` (`api/v{version}/Directory`) sert l'Annuaire
   Santé de l'ANS ; le `GET /v1/directory/self` prévu serait tombé dessus. Le registre n'expose
   **aucune route** — garde-fou `RegistryNamingGuardTests`.
3. ~~**Schéma en SQL, pas en migration FluentMigrator.** L'exécuteur du produit applique son
   assembly à **chaque base praticien** : y ajouter les tables du registre les créerait dans les
   mille bases du parc.~~

   > ⚠️ **Écart refusé par l'humain, corrigé le 2026-09-13.** Le constat était juste, la conclusion
   > non : la frontière n'est pas *« pas de FluentMigrator »*, c'est **`TypeFilterOptions`**
   > (`Namespace` + `NestedNamespaces`), qui borne un coureur à un jeu de migrations. Les deux jeux
   > coexistent donc dans le même assembly, séparés par leur espace de noms —
   > `…Migrations.MailDb` (appliqué à chaque base praticien, paresseusement) et
   > `…Migrations.TenantDb` (appliqué à une seule base, au démarrage). Trois tests tiennent cette
   > frontière (`TenantRegistryMigrationScopeTests`), et le verrou consultatif de provisionnement
   > est **unifié** dans `MigrationHelper` : le verrou du registre était plus faible que celui du
   > courrier sur trois points (pas de `lock_timeout` serveur, pas de `CommandTimeout`, `hashtext()`
   > au lieu d'une clé SHA-256 stable), ce qui l'aurait rendu inopérant entre pods lors d'un
   > déploiement progressif. L'unification a d'ailleurs révélé un **défaut préexistant** côté
   > courrier : budget client (300 s) **égal** au budget serveur (`5min`), en violation de
   > l'invariant que le code documentait lui-même — corrigé à 330 s.

#### Tests dédiés (57)

`PostgresTenantRegistryClientTests` (14) - `TenantRegistryContractTests` (8, portés du dépôt SDK à
la révision) - `TenantRegistryArchitectureTests` (5, **par réflexion** et non par balayage de
sources — `RepoRoot()` rend `null` sous `--artifacts-path`) - `TenantRegistrySynchronizerTests` (6)
- `TenantRegistryMigrationScopeTests` (3) - `ProvisioningLockTests` (5) -
`TenantRegistryOptionsBindingTests` (3) - `RegistryNamingGuardTests` (1) -
**`TenantRegistryIntegrationTests` (12, contre un vrai PostgreSQL)**.

> **Pourquoi 12 tests d'intégration après coup.** Les 45 premiers tournaient **tous** sur le
> fournisseur EF en mémoire — qui n'a ni index, ni contraintes, et évalue côté client ce qu'il ne
> sait pas traduire. Trois affirmations de la DOD y étaient donc **invérifiables** : « au plus une
> messagerie par défaut par compte, *garanti par la base* », l'index unique **filtré**
> `WHERE rpps IS NOT NULL`, et la traduction SQL du curseur `t.Id.CompareTo(cursor) > 0`. Les
> tests passaient au vert sans rien prouver. Les 12 tests d'intégration ferment ces trois trous,
> plus la frontière `TypeFilterOptions` (prouvée par le **schéma réellement produit**, pas par
> réflexion) et le verrou consultatif entre pods. **Effet immédiat** : le prérequis hérité inscrit
> dans la DOD de task-301 (curseur non prouvé traduisible) est **levé**.

Trois d'entre eux existent parce que le défaut qu'ils couvrent est **silencieux** :
- **adresse organisationnelle partagée** : 1 messagerie, 2 tenants, 2 bases (si le `TenantId`
  était celui de la messagerie, deux praticiens verraient les traces l'un de l'autre) ;
- **piège `MapInboundClaims`** : `FindFirstValue("sub")` rend toujours `null` ; le test échoue si
  la lecture repart sur `sub` seul ;
- **bride d'écriture** : 100 requêtes donnent 1 seule écriture d'activité.

#### Sonar — 4 itérations, delta **0**

| Métrique | Baseline | Pic | Final | Delta |
|---|---|---|---|---|
| `new_violations` | 155 | 165 | **155** | **0** |
| `new_code_smells` | 151 | 161 | **151** | **0** |
| `new_bugs` / `new_vulnerabilities` | 2 / 2 | 2 / 2 | **2 / 2** | 0 |
| `new_coverage` | 89,1 % | 89,1 % | **89,1 %** | 0 |

Corrigés : **S1854** (affectation morte — introduite par la passe `/simplify` elle-même),
**S4457** (validation d'arguments dans un corps `async`), **CA1068** x5, **CA1859** x2,
**S2699** (test sans assertion — dont la première correction était elle-même fausse : le double
levait avant d'incrémenter), **S103** x3, **S138**.

**Accepté** : S138 sur `AddApplication` — la méthode faisait déjà ~93 lignes avant les 2 lignes de
cette US (seuil 80). Non attribuable.
**QG ERROR** : `new_violations` 155 (seuil 0) et `new_security_hotspots_reviewed` 83,3 % — valeurs
**identiques avant l'US**. La new-code period du projet est une baseline large qui inclut des
tasks déjà mergées.

`conventions/csharp.md` : 3 entrées créées (S1854, S4457, CA1068), 1 compteur incrémenté
(CA1859, 3e récidive).

#### Revue de code — APPROVED, 2 suggestions reportées en DOD

Toutes deux sur des méthodes **sans appelant en production** :

1. **Curseur `t.Id.CompareTo(cursor) > 0` non prouvé traduisible en SQL** — les tests tournent sur
   le fournisseur EF **en mémoire**, qui évalue **côté client** : ils ne prouvent rien sur
   Postgres. Reporté au **DOD de task-301**.
2. **`EnsureTenantAsync` ne relit pas après `SaveIdempotentAsync`** — sur une course perdue, rend
   le tenant *tenté*, donc un `TenantId` inexistant, alors que c'est l'identifiant sur lequel le
   journal d'audit sera clé. `EnsureAccountAsync` fait la relecture correctement. Reporté au
   **DOD de task-303**.

#### Changement d'intégration continue (`sdk`)

Déclencheur élargi de `master`/`develop` à **toutes les branches**, comme `dtos-mss`. Sans cela,
aucun paquet n'aurait pu être publié depuis un `feat/*` et l'attente `gh run watch` du playbook
`/develop` aurait tourné à vide.

#### Dette laissée

- Les deux suggestions de revue (reportées en DOD de 301 et 303).
- S138 sur `AddApplication` (préexistante).
- La clé `RedisConnectionString` reste dans les `appsettings*.json` de `client-blazor` (task-305).

---


### v1.0 — task-305 : `HealthPlatform.Host.Sdk` retiré de `client-blazor`

**Statut** : `done` — PR [HealthPlatform.Client#73](https://github.com/codengine-technologies/HealthPlatform.Client/pull/73), label `awaiting-human-merge`
**Branche** : `chore/task-305-retirer-sdk-de-blazor` (base `origin/develop` @ `d4a0730`)
**Repos** : `client-blazor` (3 commits) ; `dtos-mss` (auto-inclus, **0 commit**, pas de PR)
**Cycle mesuré** : 14 min 02 s au total — `/start` 40 s, `/develop` 10 min 30 s (4 builds / 4 suites), `/review` 2 min 51 s (2 builds / 1 suite)

#### Objet

Le SDK redevient un paquet **strictement backend**, avec `api-mail` pour seul
consommateur. Préalable à task-299 : tant que `client-blazor` le référençait, tout
contrat de plateforme publié dedans (`ITenantRegistryClient`, `IAuditSink`) partait
dans la charge utile WASM du navigateur et imposait un bump de version à un
consommateur qui n'en consommait rien.

#### Constat — la référence était morte

| Fait | Preuve |
|---|---|
| `AddSdk` n'est **jamais** appelé dans `Client/Blazor/Src` | seul `AddShellService` l'est (`Src/Shell/Program.cs:63`) |
| Donc `IResilientCacheService` n'était ni enregistré ni injecté | unique occurrence dans le dépôt : le commentaire de `Src/Shell/Extensions/ServiceCollectionExtensions.cs:23` affirmant le contraire — **faux**, reliquat de task-218 |
| `using HealthPlatform.Host.Sdk.Services;` mort | `Src/Shell/Extensions/ServiceCollectionExtensions.cs:2`, aucun type du SDK utilisé dans le fichier |
| `IMarkdownService` / `MarkdownService` dupliqués | `Src/Component/Shared/Services/IMarkdownService.cs` + `Src/Modules/Mss/Plugin/Services/MarkdownService.cs` ; les 7 `@inject IMarkdownService` résolvent le contrat Blazor |
| `ICacheService` dupliqué | `Src/Component/Shared/Services/ICacheService.cs` + `InMemoryCacheService` — contrat différent de celui du SDK |
| Assembly expédié au navigateur | `HealthPlatform.Components.Shared.csproj` porte `<SupportedPlatform Include="browser" />` |

#### Deux dépendances transitives — le fichier de task n'en annonçait qu'une

Le §Piège de `todo-task-305.md` qualifiait `Markdig` de « seul effet de bord réel ».
**C'était faux**, et le build l'a montré au retrait. Le task file a été corrigé.

1. **`Markdig`** — réellement utilisé par `Src/Modules/Mss/Plugin/Services/MarkdownService.cs:1`
   sans `PackageReference` propre. Déclaré explicitement **dans un commit séparé,
   avant le retrait** (`Directory.Packages.props` + `HealthPlatform.Module.Mss.Plugin.csproj`,
   version `0.40.0` — celle qu'apportait le SDK), pour que le build ne soit jamais rouge.
2. **`Microsoft.Extensions.Caching.StackExchangeRedis`** — alimentait l'unique
   `AddStackExchangeRedisCache` de `Src/Shell/Extensions/ServiceCollectionExtensions.cs`.
   Enregistrement **inerte**, vérifié : aucun `IDistributedCache` injecté dans
   `Client/Blazor/Src` (grep), pas de `AddSession` / `UseSession`, pas de
   `AddOutputCache`, pas de backplane SignalR, et `AddDataProtection()`
   (`Src/Shell/Program.cs:57`) est **en mémoire** (pas de `PersistKeysToStackExchangeRedis`).
   Le seul consommateur possible aurait été le `CacheService` du SDK, enregistré par
   `AddSdk` — jamais appelé. **Retiré** avec son paramètre `IConfiguration`, devenu
   sans objet (appelant unique mis à jour : `Program.cs:63`).

La clé `RedisConnectionString` est **laissée** dans `appsettings.json` /
`appsettings.Test.json` : la retirer toucherait la surface de déploiement pour un
gain nul.

#### Fichiers touchés

| Fichier | Changement |
|---|---|
| `Directory.Packages.props` | `-PackageVersion HealthPlatform.Host.Sdk 12.0.0` ; `+PackageVersion Markdig 0.40.0` |
| `Src/Component/Shared/HealthPlatform.Components.Shared.csproj` | `-PackageReference HealthPlatform.Host.Sdk` |
| `Src/Modules/Mss/Plugin/HealthPlatform.Module.Mss.Plugin.csproj` | `+PackageReference Markdig` |
| `Src/Shell/Extensions/ServiceCollectionExtensions.cs` | `using` morts retirés, `AddStackExchangeRedisCache` retiré, signature sans `IConfiguration`, commentaire faux de task-218 corrigé |
| `Src/Shell/Program.cs` | appelant unique de `AddShellService` mis à jour |
| `tests/…/SdkReferenceGuardTests.cs` | **nouveau** — garde-fou anti-récidive (2 tests) |
| `tests/…/RepoScan.cs` | **nouveau** — helper partagé (passe qualité) |
| `tests/…/ClientSensitiveDataScanTests.cs` | refactor : délègue `RepoRoot` / `git ls-files` à `RepoScan` |

#### Garde-fou anti-récidive

`SdkReferenceGuardTests` — 2 tests :
- `ProductionProjects_DoNotReferenceTheBackendSdk` : aucun `Include="HealthPlatform.Host.Sdk"`
  dans `Src/**/*.csproj` ni `Directory.Packages.props` ;
- `ProductionSources_DoNotImportTheBackendSdk` : aucun `HealthPlatform.Host.Sdk.` dans
  `Src/**/*.{cs,razor}`, **hors lignes de commentaire** — documenter le retrait est le
  sujet de la task.

Deux précautions méthodologiques :
- **Vérifié par réinjection de la régression** : la ligne `PackageVersion` remise dans
  `Directory.Packages.props` fait virer le test au rouge, en pointant
  `Directory.Packages.props:8`. Puis restauré.
- **Protégé du faux vert** par `Assert.NotEmpty(files)` : si `git ls-files` échouait ou
  si `RepoRoot()` se résolvait mal, les deux assertions passeraient **à vide**. Un test
  qui ne peut pas échouer est pire qu'un test absent.
- `tests/` est exclu du scan : ce fichier nomme le paquet, un guard qui échoue sur
  lui-même est du bruit.

#### Passe qualité (`/simplify`, sous-étape de `/develop`)

**Reuse** : les deux gardes de balayage du dépôt (task-184 données sensibles, task-305
référence SDK) avaient chacune leur copie de « remonter jusqu'au `.sln`, puis
`git ls-files` ». Extraites dans `RepoScan` (`RepoRoot()`, `TrackedFiles(root, filter)`).
Deux copies d'un helper de parcours dérivent, et la dérive est invisible puisque chaque
garde continue de passer sur ses propres termes. Refactor fidèle : filtre et sémantique
identiques (`Src/Modules/Mss/` + `.cs|.razor`), `IEnumerable` → `List` (consommé une fois
en `foreach`). **184 tests verts avant comme après.**

#### Validation

- `dotnet build HealthPlatform.Client.sln` : **0 erreur, 0 avertissement**
- `dotnet test HealthPlatform.Client.sln` : **184 réussis / 0 échec / 2 ignorés**
  (skips préexistants de `BiologyAckPanelComponentTests`)
- `dotnet build HealthPlatform.Dtos.Mss.csproj` : 0 erreur (branche sans commit)
- `/sonar`, `/lint-angular`, `/lint-mobile`, `/verify-visual` : **skipped** — repos non touchés

#### Code review — APPROVED, 0 bloquant, 2 suggestions

1. **`ClientSensitiveDataScanTests` peut passer à vide.** Ce garde-fou de sécurité
   (task-184 : INS dans les URLs, journalisation nominative) n'assert pas que son
   énumération de fichiers est non vide : si `git ls-files` échouait, il passerait
   **sans rien garder**. Le nouveau `SdkReferenceGuardTests` s'en protège ; l'ancien
   mérite le même `Assert.NotEmpty`, d'autant qu'il partage désormais `RepoScan`.
   **Faiblesse préexistante**, non introduite par cette task.
2. **Deux résidus morts possibles** : `Microsoft.AspNetCore.DataProtection.StackExchangeRedis`
   reste déclaré dans `Directory.Packages.props` alors qu'`AddDataProtection()`
   (`Program.cs:57`) est en mémoire ; et trois `using` de `ServiceCollectionExtensions.cs`
   (`Ardalis.Result`, `System.Net`, `System.Net.Http.Headers`) ne correspondent à aucun
   type du fichier après nettoyage. `/review` est en lecture seule sur le code —
   signalés, pas corrigés.

#### Dette laissée

- Les deux suggestions ci-dessus, candidates à une task d'hygiène.
- `RedisConnectionString` reste dans les `appsettings*.json` (choix assumé).

---

## Annexe A — Cartographie des briques applicatives

### Contrats de plateforme (`TenantRegistry` livré par task-299 ; `Audit` à venir, task-300)

| Brique | Emplacement prévu | Rôle |
|---|---|---|
| `ITenantRegistryClient` + DTOs | `Sdk/TenantRegistry/V1/` | **Livré** (task-299) — comptes, messageries, tenants, dormance. Paquet `14.0.0` |
| `PostgresTenantRegistryClient` | `Api/Mail/src/Infrastructure/TenantRegistry/` | **Livré** (task-299) — seule implémentation ; test d'architecture (par réflexion) garantit que le `DbContext` n'est référencé nulle part ailleurs |
| `IAuditSink` / `IAuditReader` | `Sdk/` — `HealthPlatform.Host.Sdk.Audit.V1` | Contrat du journal mutualisé (écriture par lots / lecture scopée tenant) |

> **Nommage — piège connu.** `DirectoryController` (`api/v{version}/Directory`,
> `AnnuaireSanteService`) sert l'**Annuaire Santé de l'ANS** (`practitioners/search`,
> `specialties`, `professions`). Le registre de cet EPIC n'a rien à voir : ses
> identifiants portent **`TenantRegistry`**, jamais `Directory`, et il n'expose aucune
> route sous `/directory`.

### Briques touchées par task-305

| Brique | Emplacement | État |
|---|---|---|
| `RepoScan` | `Client/Blazor/tests/HealthPlatform.Module.Mss.Plugin.Tests/RepoScan.cs` | Helper partagé des gardes de balayage |
| `SdkReferenceGuardTests` | même répertoire | Garde-fou anti-récidive du retrait du SDK |
| `ServiceCollectionExtensions.AddShellService` | `Client/Blazor/Src/Shell/Extensions/` | Signature sans `IConfiguration` depuis task-305 |

---

## Annexe B — Inventaire fonctionnel (2026-09-13)

| Grandeur | Valeur |
|---|---|
| Tasks déclarant `**Epic**: E016` | 7 (299, 300, 301, 303, 304, 305, 306) |
| Tasks `done` | 2 (task-299, task-305) |
| Tasks `todo` | 5 |
| Questions ouvertes bloquantes | 1 (`questions/task-302.md` — identité et habilitation des administrateurs) |
| PRs ouvertes | 2 (Host.Sdk#3, Api.Mail#233 — `awaiting-human-merge`) ; 1 mergée (Client#73) |
| Paquets NuGet publiés par l'EPIC | 1 (`HealthPlatform.Host.Sdk 14.0.0`) |
| Consommateurs du SDK après task-305 | **1** (`api-mail`) — contre 2 avant |

---

## Annexe C — Tasks ayant contribué à cet EPIC

| Task | Apport | Repos | Statut |
|---|---|---|---|
| task-299 | Registre des tenants : comptes (`sub` Keycloak + RPPS), messageries, **tenants** (compte × messagerie, porteurs de la base isolée et de `TenantId`), horodatages de connexion et dormance. Contrat `ITenantRegistryClient` et implémentation Postgres dans `api-mail` — **le contrat a quitté le SDK à la révision du 13/09** | `api-mail` (`sdk` : CI seulement) | ✅ **done** (PR Sdk#3, Api.Mail#233) |
| task-300 | Journal d'audit en base commune : table partitionnée par mois, `TenantId` = id du **tenant**, RLS + rôles lecture/écriture séparés, purge planifiée s'appuyant sur `AuditRetentionPolicy.FamilyOf`, lecture double source transitoire | `api-mail` | ✅ **mergée** (`ff6332f7`) |
| task-301 | Reprise de l'historique d'audit à débit borné (≤ 4 bases simultanées), vérification par comptage par tenant, puis retrait de la lecture double source par tenant. **⚠️ Intégralement retirée par task-312** : la reprise n'a jamais été exécutée sur un parc réel, et l'état final a été atteint par suppression — aucune donnée de production n'étant en jeu | `api-mail` | ✅ **mergée**, puis **annulée** (task-312) |
| task-303 | Vague 1 multi-BAL : la boîte devient une sélection par requête validée contre le registre **et** l'identité PSC ; disparition des claims `mssEmail`/`mssSub`/`mssRpps` ; bascule = fin de session + nouvelle session (garde `SESSION_MAILBOX_MISMATCH`) ; `AuditActionType` + 5 membres | `api-mail`, `dtos-mss` | ✅ **done** (PR Api.Mail#236, Dtos.Mss#32 — **`awaiting-human-merge`** depuis task-304 : la US est complète) |
| task-304 | Vague 2 multi-BAL : onboarding par le registre, écran de sélection, avatar → sélecteur, gestion des comptes, purge totale de l'état à la bascule — parité Blazor / Angular / mobile. **L'outillage de capture visuelle n'a pas pu être remis à niveau** : `Tools/visual-verify/` n'est pas versionné et donc absent du poste (cf. `questions/task-304.md`) | `client-blazor`, `client-angular`, `client-mobile` | ✅ **done** (PR Client#74, Mobile#70 — `awaiting-human-merge` ; Angular en code-only) |
| task-305 | **Le SDK redevient backend-only** : retrait de la référence morte dans `client-blazor`, déclaration explicite de `Markdig`, retrait de l'enregistrement Redis inerte, garde-fou anti-récidive | `client-blazor` | ✅ done |
| task-308 | Le registre sépare ses deux identités : `accounts` ne dit plus que Keycloak (`sub`, email, username), l'identité PSC (`psc_subject` + `rpps`) vit sur le rattachement. Un **seul écrivain** pour `mss_accounts` — l'onboarding explicite, précédé d'une sonde XOAUTH2 validée par l'opérateur | `api-mail`, `client-blazor`, `client-mobile`, `client-angular` | ✅ **mergée** (PR Api.Mail#238) |
| task-312 | **Retrait du journal d'audit hérité** (`MssAuditTraces`, son dépôt, la lecture double source, la machinerie de reprise et ses deux bornes) et **branchement de la purge de rétention mutualisée**, qui n'avait aucun appelant. Estampillage du tenant à la source sur les trois traces de messagerie ; tenant sentinelle `Guid.Empty` pour le résiduel. Tri de l'écran d'audit rapatrié — il n'existait plus que côté hérité | `api-mail` | ✅ **done** (PR Api.Mail#239, `awaiting-human-merge`) |
| task-309 | **Le sélecteur de messagerie devient atteignable** : montage de `<mss-mailbox-switcher />` dans un en-tête créé pour lui sur la page Messagerie Angular (il n'était monté nulle part), entrée `NAV_ITEMS` « Mes messageries » (`accounts`, avant-dernière), conversion design system à `data-testid` constants. **+23 tests** là où les trois sélecteurs n'en avaient aucun, dont **3 contre-épreuves de montage**. Pose sur les trois fronts la garde « rattacher exige une session PSC » dans le code, où elle ne tenait qu'à un attribut `disabled` | `client-angular`, `client-mobile`, `client-blazor` | ✅ **done** (PR Client#76, Mobile#72, `awaiting-human-merge` ; Angular en code-only) |
| task-306 | Banc de charge multi-BAL : dimension « boîtes par compte », parcours avec bascule réelle, restitution du coût de bascule. **⛔ ABANDONNÉE le 2026-09-15** (décision humaine) — la task file est supprimée. Ce dont elle dépendait a été livré par task-311 (le seeder provisionne le registre) et un tir de référence 500 praticiens a été mené le 2026-09-15 : `report-journey-mssante-n500-155118.md`. La dimension « boîtes par compte » n'est donc pas mesurée, et ne le sera pas | `api-mail` | ⛔ **abandonnée** |
| task-311 | **Le banc redevient mesurable** : le seeder écrit lui-même les deux lignes de registre que l'onboarding écrirait (`accounts` + `mss_accounts`), par le câblage de production (`AddTenantRegistryClient` + `ITenantRegistryClient`), identités issues de `LoadTestPlanGenerator`. Sans elles, task-308 laissait **toutes** les routes de messagerie en `403 MAILBOX_NOT_ATTACHED` et `TenantId` nul — donc le journal mutualisé jamais exercé. Corrige au passage la parité du bootstrap du registre (`TenantRegistryBootstrap` : migration **et** partitions d'audit) | `api-mail` | ✅ **done** (PR Api.Mail#240, `awaiting-human-merge`) |

### Question ouverte

| Fichier | Objet | Blocage |
|---|---|---|
| `questions/task-302.md` | Accès des administrateurs et de la sécurité au journal mutualisé | **Aucun modèle de rôles n'existe dans `api-mail`** : la politique globale est `RequireAuthenticatedUser()` seule (`Program.cs:133`) et le gate de rôle « Doctor » a été désactivé le 2026-05-11 (`BiologyAcksController.cs:15`). Ouvrir un accès transverse dans cet état le rendrait accessible à tout utilisateur authentifié, sur un historique porteur de données de santé de tout le parc |

---

*Document vivant, régénéré par la forge à chaque fin de cycle. La vue produit vit dans
[`E016-socle-multi-tenant.md`](./E016-socle-multi-tenant.md).*
