# task-401 — Délégation de BAL : retirer le modèle `shared/`, que Mailiz ne déploie plus

**Repos**: dtos-mss, api-mail, client-mobile, client-angular
**Dependencies**: aucune. task-397, task-398 et task-399 sont mergées. task-400 est **gelée**
(`questions/task-400.md`) et n'est pas un prérequis.
**Epic**: E009
**Priorité**: **2** — le code est inerte en production, donc rien ne casse aujourd'hui. Mais il
simule un modèle que Mailiz n'offre plus. Le banc, la règle 14 et le catalogue e2e décrivent une
réalité fausse, et toute task de délégation qui s'appuierait dessus partirait de travers.

> **Constat (humain, 2026-10-27)** : Mailiz ne déploie plus l'espace de noms IMAP
> `shared/<adresse du délégant>/…`. Selon l'ANS, le délégataire se connecte **directement à la BAL
> du délégant** avec **son propre jeton PSC** : XOAUTH2, avec l'adresse du délégant pour
> identifiant. Exemple : Cyril ouvre la BAL `virginie.medecinrpps0062267@medecin.formation.mssante.fr`
> une fois que Virginie lui a donné les droits. L'humain l'a vérifié sur l'environnement de
> formation.
>
> **Ce que cette task ne fait pas** : elle ne livre pas la délégation version ANS. La bascule d'une
> BAL à l'autre par le registre, et la façon de détecter qu'il s'agit d'une délégation, font l'objet
> d'une étude séparée, puis d'une nouvelle US.

## Ce qui est établi (essai de revert à blanc, 2026-10-27)

| Dépôt | Commits à revert (squash) | Conflits | Volume |
|---|---|---|---|
| api-mail | `f02356fc` (399), `84988dda` (398), `47a94d4f` (397), dans cet ordre | mécaniques : version du paquet DTOs dans `Directory.Packages.props` et `packages.lock.json`. **4 fichiers de code**, voir ci-dessous | 144 fichiers, −9 370 lignes |
| dtos-mss | `55fac68` (399), `ed31ab9` (398) | aucun | 5 fichiers, −90 lignes |
| client-mobile | `f03ca5c` (399), `9594424` (398) | aucun | 56 fichiers, −3 647 lignes |
| client-angular | commits non identifiables par la forge (TFS, sans identifiant de task) | — | voir la décision 3 |

Les **4 conflits de code** d'api-mail viennent de task-389 (HPRIM). Elle avait seulement ajouté la
détection HPRIM au chemin de lecture **délégué** :

- `src/Application/Services/Implementation/ImapService.Delegation.cs` → supprimé ;
- `tests/mss.mail.api.tests/Architecture/DelegatedPersistenceGuardScanTests.cs` → supprimé ;
- `tests/mss.mail.integration.tests/UseCases/DelegationEndToEndTests.cs` → supprimé ;
- `tests/mss.mail.integration.tests/UseCases/UseCaseHttpHost.cs` → garder la version de `develop`,
  puis retirer le `using mss.mail.application.Delegation` et les enregistrements de délégation.
  C'est la seule erreur de compilation restante à l'essai.

Après résolution, `src/` compile sans erreur. Il n'y a **aucune migration de base** ni aucun
feature flag dans les trois commits. Seuls `src/AppHost/AppHost.cs`,
`src/AppHost/dovecot/delegation.conf` et `dovecot.conf` touchent à l'AppHost.

## Décisions actées (humain, 2026-10-27)

1. **Retrait par revert git des commits squashés**, sur la branche de la task, dans chaque dépôt
   pushable. Pas de retrait à la main : le revert garde le lien avec les commits d'origine, et le
   code reste récupérable dans l'historique pour la réécriture.
2. **dtos-mss : nouvelle version publiée sans les champs**, jamais un retour à une version
   antérieure. Les consommateurs .NET sont remontés sur cette version.
3. **client-angular** : *à acter, voir les notes de cadrage.*
4. **Règle 14 : le principe reste, la technique tombe.** « Rien de ce qui vient d'une BAL déléguée
   n'est persisté ni exploité chez le délégataire » reste vrai juridiquement : le délégant reste
   responsable du secret professionnel. Ce qui tombe, c'est sa mise en œuvre par le chemin
   `shared/` : le préfixe, la garde unique par chemin, le masquage `shared/<adresse>/…` et le cache
   délégué. La réécriture viendra avec l'étude du registre.
5. **task-389 à 392 (HPRIM) ne régressent pas** sur une BAL propre.

## Objective

Ramener `develop` à un état où plus rien ne suppose l'espace IMAP `shared/` : le code, le
contrat, le banc, le catalogue e2e et les consignes de la forge. Pour un médecin sans délégation,
rien de visible ne change : le code retiré ne s'exécutait jamais contre Mailiz. Le principe
juridique de la règle 14 est conservé pour la future délégation par session.

## Règles

- **Ordre des revert** : du plus récent au plus ancien (399, puis 398, puis 397), avec une
  résolution complète après chaque revert. Git refuse d'enchaîner un revert sur des conflits non
  résolus, et un revert « réussi » peut alors n'avoir rien appliqué : c'est arrivé à l'essai.
- **Version DTOs** : dans les conflits de `Directory.Packages.props` et des lock files, garder la
  version de `develop`, puis monter sur la nouvelle version publiée par cette task.
- **HPRIM intact** : la détection HPRIM d'une BAL propre (`MedicalSourceParts`, task-389) n'est
  pas dans les fichiers supprimés. Elle ne doit pas bouger.
- **Catalogue e2e** : les scénarios `E2E-DELEG-001` à `007` sont **retirés** de
  `Api/Mail/e2e/scenarios.yml`, et leurs implémentations sont retirées des deux clients, pour que
  la porte de parité reste verte. Pas de quarantaine ni de divergence : ces parcours n'existent plus.
- **Plan de contrôle** (relu par l'humain avant le push, règle d'or 7) :
  - `CLAUDE.md`, règle 14 : garder le titre, le principe et le « Pourquoi ». La partie technique
    `shared/` (espace de noms, garde par chemin, masquage, cache, exceptions liées au chemin) est
    remplacée par une mention « mise en œuvre retirée par task-401, à réécrire pour la délégation
    par session (ANS, 2026-10-27) » ;
  - `agents/po.md`, garde-fou « BAL déléguée » : même traitement. Le principe reste, la mention
    des dossiers `shared/<adresse>/…` et du banc de délégation disparaît ;
  - `conventions/*.md` : une entrée dont la consigne ne vaut que pour `shared/` est marquée
    **caduque (task-401)**, avec son compteur figé. Une entrée dont la leçon est générale reste
    telle quelle (exemple : `retrait-sur-liste-perimee`). La ligne du registre des flaky sur
    `E2E-DELEG-004` est retirée ;
  - `Docs/audits/delegation-bal-*-20261025.md` : conservés pour l'histoire, avec en tête un
    encadré « modèle `shared/` caduc depuis le 2026-10-27 ».
- **task-400** reste gelée. Elle n'est ni rebasée ni supprimée. Sa branche api-mail repose sur
  task-397 : elle sera reprise après l'étude du registre.

## Definition of Done

- [ ] api-mail : revert de `f02356fc`, `84988dda` et `47a94d4f` sur la branche de la task, conflits
      résolus selon les règles. `git grep -i "shared/" -- src` ne renvoie plus aucune occurrence
      liée à la délégation.
- [ ] api-mail : `src/AppHost/dovecot/delegation.conf` retiré, et `AppHost.cs` et `dovecot.conf`
      sans le banc de délégation.
- [ ] dtos-mss : revert de `55fac68` et `ed31ab9`. **Nouvelle version** publiée, et api-mail
      remonté dessus. Types TypeScript alignés dans client-mobile et client-angular.
- [ ] client-mobile : revert de `f03ca5c` et `9594424`. Build et tests verts.
- [ ] client-angular : le code de délégation de task-398 et task-399 est retiré (section des BAL
      déléguées, choix de la BAL émettrice, `delegated-mailbox.util`, specs e2e `E2E-DELEG-*`).
      Build et tests verts. Code seul, sans git.
- [ ] Build OK (0 erreur) sur dtos-mss, api-mail, client-mobile et client-angular.
- [ ] Tests OK (0 échec) sur api-mail, client-mobile et client-angular. Le total des tests passés
      est comparé avant et après : seuls les tests de délégation disparaissent.
- [ ] Non-régression HPRIM : les tests d'intégration HPRIM de task-389 à 392 restent verts, tout
      comme les scénarios `E2E-BIO-*` sur les deux voies.
- [ ] Test d'intégration (règle 1b) : **non applicable**, aucun comportement observable ne change
      pour une BAL sans délégation, puisque le code retiré ne s'exécutait que sous `shared/`. Le
      filet est fait des suites d'intégration existantes (dossiers, envoi, brouillons, HPRIM),
      toutes vertes, et du rejeu e2e complet.
- [ ] Catalogue : `E2E-DELEG-001` à `007` retirés de `Api/Mail/e2e/scenarios.yml`, et leurs
      implémentations retirées des deux clients. `/e2e` est vert sur les deux voies, porte de
      parité comprise.
- [ ] Plan de contrôle mis à jour selon les règles (règle 14, `agents/po.md`, `conventions/*.md`,
      encadrés des analyses). Relu par l'humain avant le push.
- [ ] Aucune donnée de santé en clair dans les logs : inchangé, le masquage central générique
      reste en place.

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`.
- Lancer le mobile (`cd Client/Mobile && npm start`) et weda2 (`cd Client/Angular/front && npm start`).
- Se connecter avec un compte praticien **sans délégation** :
  - la liste des dossiers est identique à celle de `develop` avant la task, sans section
    « BAL déléguées » ;
  - lire un message, répondre, enregistrer un brouillon puis l'envoyer : l'envoi part sans
    demander de BAL émettrice ;
  - ouvrir un résultat HPRIM : document de biologie, résultats et anomalie du biologiste
    affichés comme avant.
- Se connecter avec le compte délégataire de formation (Cyril) : aucune BAL déléguée n'apparaît,
  et aucune erreur ne s'affiche. C'est le comportement attendu tant que la délégation par session
  n'est pas livrée.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — retrait d'une fonctionnalité Mailiz sans exigence DSR publiée
- **Exigences DSR honorées** : non applicable — aucune exigence n'était couverte par le modèle
  `shared/`
- **INS** : non applicable — aucun traitement patient n'est ajouté ni modifié. HPRIM et CDA sont
  inchangés sur une BAL propre.
- **Authentification PS** : inchangée — PSC / e-CPS, XOAUTH2 sur la BAL du praticien
- **Habilitations** : la délégation n'est plus proposée. Aucun accès à la BAL d'un tiers ne reste
  ouvert par l'application.
- **Interop CI-SIS** : inchangé — IHE-XDM, CDA r2 via `interop-cda`, HPRIM
- **Tracé PGSSI-S** : inchangé. L'audit des actes délégués de task-397 disparaît avec eux, et
  l'imputabilité de task-400 est gelée.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : la mention « accès et envoi au nom d'un délégant », ajoutée pour
  task-399, est **suspendue**. Elle sera à reprendre avec la délégation par session.

## Notes de cadrage

- **Décision 3 à acter : comment retirer le code Angular ?** La forge ne lit pas l'historique TFS
  de weda2 : les commits de task-398 et task-399 n'y portent pas d'identifiant de task. Deux voies :
  - **(a)** l'humain fournit les SHA, et revert lui-même sur sa branche ;
  - **(b)** `/develop` retire le code à la main en mode code seul, guidé par la liste du DoD et par
    le diff des revert mobile et api-mail. L'humain commit ensuite.

  À défaut de réponse, la voie (b) s'applique.
- **Le code weda2 de task-400 n'est pas commité** (33 fichiers). L'humain le met de côté
  (`git stash push -m "task-400 gel"`) avant `/start task-401`, pour que le retrait ne le mélange
  pas.
- **Pré-flight de `/start`** : la copie `Api/Mail` est encore sur
  `feat/task-400-delegation-tracer-ce-qui-agit`. La repasser sur `develop` avant `/start`.
- **Étude suivante** (hors task) : bascule d'une BAL à l'autre par le registre, et détection d'une
  délégation (la personne qui agit, identifiée par le RPPS de son jeton, n'est pas le titulaire de
  la BAL). Une question à trancher : écrire dans le tenant du délégant, est-ce « persister chez le
  délégataire » au sens de la règle 14 ?

## Branches

- `api-mail` (pushed) : feat/task-401-delegation-retrait-du-modele-shared — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-401-delegation-retrait-du-modele-shared
- `client-mobile` (pushed) : feat/task-401-delegation-retrait-du-modele-shared — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-401-delegation-retrait-du-modele-shared
- `dtos-mss` (paresseuse) : branche créée par `/develop` au moment du revert du contrat
- `client-angular` (code-only) : forge writes code on the branch currently checked out in `Client/Angular/` (`feature/nova-mss-weda-integration` au /start, arbre propre) — humain gère branche, commit, push, PR TFS. Décision 3 non tranchée : voie (b) par défaut, retrait à la main par `/develop`.

## Timings

*(généré par `tools/timing/report.sh --task task-401 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 38 s | — | — | — | — |
| /develop | ok | 13 min 08 s | 4 (36 s) | 3 (5 min 31 s) | — | dtos-mss 1B/0T, api-mail 1B/1T, client-mobile 1B/1T, client-angular 1B/1T |
| /sonar | ok | 8 min 59 s | 1 (23 s) | 5 (6 min 32 s) | 2 (42 s) | api-mail 1B/5T |
| /lint-angular | ok | 52 s | — | — | — | — |
| /lint-mobile | ok | 24 s | — | — | — | — |
| /e2e | ok | 16 min 25 s | — | — | — | e2e ×3 (15 min 17 s) |
| /review | ok | 6 min 30 s | 4 (28 s) | 3 (4 min 35 s) | — | api-mail 1B/1T, dtos-mss 1B/0T, client-mobile 1B/1T, client-angular 1B/1T |
| /tech-writer | ok | 1 min 14 s | — | — | — | — |
| **Total cycle** | | **48 min 13 s** | **9 (1 min 28 s)** | **11 (16 min 39 s)** | **2 (42 s)** | |

Autres commandes mesurées : lint ×2 (25 s), nuget-wait ×1 (18 s), restore ×1 (2.9 s)

## Develop log

- **Pré-flight** : deux tasks en `wip` (task-400 gelée par décision humaine du 2026-10-27, documentée ;
  task-401). État connu, non bloquant. `interop-cda` vérifié sur `develop` sous
  `interop/interop.cda.parser` (le tableau de CLAUDE.md disait `interop` : corrigé, voir plus bas).
- **Repos touchés** : dtos-mss, api-mail, client-mobile, client-angular.
- **DTOs publiés** : 544.0.0 (develop) → **548.0.0** (revert de `55fac68` et `ed31ab9`, run CI
  `40552539796`). api-mail remonté, lock files compris.
- **Interop** : aucun changement.
- **Commits** :
  - dtos-mss : `28817cd` revert(dto) — task-398 et task-399 ;
  - api-mail : `49e44ce0` revert 399 (sans conflit), `13035da2` revert 398 (conflits mécaniques :
    version DTOs et 13 lock files gardés à develop, `DelegationEndToEndTests.cs` gardé puis supprimé
    au revert suivant), `3b67bba5` revert 397 (conflits : `ImapService.Delegation.cs`,
    `DelegatedPersistenceGuardScanTests.cs`, `DelegationEndToEndTests.cs` supprimés ;
    `UseCaseHttpHost.cs` version develop sans les `using` de délégation), `0225c9b5` bump DTOs 548 ;
  - client-mobile : `be4193a` revert 399, `b96b12a` revert 398 (sans conflit) ;
  - client-angular (code seul, **non commité**, sur `feature/nova-mss-weda-integration`) : diffs
    inverses des commits TFS `f0b2417b` (Task 399) puis `f37bcba2` (Task 398), identifiés en lecture
    seule. 58 fichiers (46 modifiés, 12 supprimés), −5 522 lignes. Appliqués avec `patch -R`, fin de
    ligne choisie fichier par fichier (l'arbre mêle CRLF et LF). Exclus : `front/.claude/compact-log.txt`
    (journal d'outil, pas du code). `mail-detail.component.scss` (fins de ligne mêlées dans le fichier)
    retiré à la main : bloc `.mail-detail-delegation-banner`.
- **Reliquats vérifiés** : `git grep -i "shared/" -- src` vide sur api-mail ; aucun `E2E-DELEG` au
  catalogue ni dans les specs des deux clients ; les seuls « delegat » restants côté Angular sont des
  « delegates to » en anglais ; `src/AppHost/dovecot/delegation.conf` retiré.
- **Build / tests locaux** :
  - dtos-mss : build 0 erreur ;
  - api-mail : build 0 erreur, 0 avertissement ; tests 0 échec : domain 195, infrastructure 695,
    api 1 288, application 3 748, intégration 1 011 + 16 ignorés (sur 1 027) — AppHost de dev actif
    sur le poste, sans effet ;
  - client-mobile : build OK (avertissements de budget SCSS et NG8107 préexistants), 1 302/1 302 ;
    type-check e2e OK ;
  - client-angular : build `weda2` OK, `mss-lib` 1 298/1 298 (118 fichiers) ; type-check e2e
    `mss-e2e` OK.
- **Totaux avant / après** (listage `--list-tests` de `origin/develop` dans un worktree) : api
  1 355 → 1 288 (−67), application 3 826 → 3 737 (−89), intégration 1 072 → 1 030 (−42) ; domain
  264 → 195 (−69), infrastructure 701 → 695 (−6) ; mss-lib 1 358 → 1 298 (−60). Les fichiers
  retirés ou modifiés sont tous des tests de délégation ou leurs points d'appel.
- **Non-régression HPRIM** : la détection HPRIM d'une BAL propre (`MedicalSourceParts`) n'est pas
  dans les fichiers supprimés ; les tests d'intégration HPRIM passent dans la suite verte. Les
  scénarios `E2E-BIO-*` sont rejoués par `/e2e`.
- **Règle 1b** : non applicable, comme le dit la DoD. Aucun comportement observable ne change pour une
  BAL sans délégation.
- **Passe qualité (/simplify)** :
  - Aucune simplification appliquée : api-mail, client-mobile, client-angular. Le diff est un retrait
    pur par revert ; les lignes « ajoutées » sont le code d'avant la délégation, restauré tel quel.
  - Contrôles mécaniques §Q 2b sur api-mail : aucune occurrence.
  - Ignoré (porteur de contrat) : dtos-mss.
- **Plan de contrôle** (non commité, **à relire par l'humain avant le push**, règle d'or 7) :
  - `CLAUDE.md` règle 14 : encadré « mise en œuvre retirée le 2026-10-27, principe maintenu » ;
    journaux, garde et refus de `/review` reformulés sans le chemin `shared/` ;
  - `CLAUDE.md`, tableau des dépôts : `interop-cda` sous `interop/interop.cda.parser`, et la consigne
    de vérifier `--show-prefix` plutôt que le tableau (chemin changé trois fois) ;
  - `agents/po.md` : garde-fou « BAL déléguée » aligné ;
  - `conventions/csharp.md` : `delegated-access-ouvre-le-corps` marquée caduque, compteur figé ;
  - `conventions/e2e.md` : ligne du registre des flaky `E2E-DELEG-004` retirée. Les leçons générales
    (`retrait-sur-liste-perimee`, `inbox-laissee-en-l-etat`, `regle-transverse-tous-les-specs`)
    restent ;
  - `Docs/audits/delegation-bal-*-20261025.md` : encadré « modèle `shared/` caduc ».
- **DOD self-check** : 10/12 vérifiés par commande. Restent à `/e2e` (voies et parité) et à la relecture
  humaine du plan de contrôle.
- **Next step** : `/sonar task-401`.

## Sonar log

- Serveur : 9.9.8.100196 sur `http://127.0.0.1:9000` (mesuré : `docker port sonarqube` → 9000), propriété
  `sonar.login`. Une analyse complète (begin, build Release, 5 suites OpenCover, end).
- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 96,8 %. Aucune issue, aucun hotspot à revoir.
- Phase 1 — Issues fixées : 0. Tests ajoutés : 0 (diff de retrait pur).
- Phase 2 (legacy) : non jouée, 0 issue ouverte sur le projet.
- Build / tests : ✓ verts sous couverture (domain 195, application 3 748, infrastructure 695,
  api 1 288, intégration 1 011 + 16 ignorés).
- `conventions/csharp.md` : rien à alimenter, aucune correction manuelle.

### KPIs qualité (baseline → final)

La baseline est la dernière analyse du serveur (task-400, 2026-10-27 17:01 UTC).

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 95,1 % | 96,8 % | +1,7 pt |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 | 0 |
| Coverage (projet) | 97,4 % | 98,0 % | +0,6 pt |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

- Mode : chaîné. Contournement task-367 : `npx nx run-many -t lint --projects=mss-lib,mss-e2e`, puis
  `npx eslint --format json` sur les fichiers modifiés par la task, avec attribution aux lignes ajoutées
  par `git diff -U0`.
- Scope : `mss-lib` (53 fichiers de la task) et `mss-e2e` (5 fichiers). Branche
  `feature/nova-mss-weda-integration`, arbre non commité (code seul).
- Baseline : **0 erreur** ; avertissements `mss-lib` 43 (niveau d'avant task-399), `mss-e2e` 57.
- Avertissements sur les lignes ajoutées par la task : **0** (70 messages dans les 41 fichiers modifiés,
  tous préexistants).
- Itérations : 0 / 5. Pas d'auto-fix : avec 0 erreur, il n'aurait touché que des avertissements
  préexistants, hors du périmètre de la task (règle 6).
- Build / tests : ceux de `/develop`, inchangés depuis : build `weda2` OK, `mss-lib` 1 298/1 298.
- `conventions/angular.md` : rien à alimenter.

## Lint mobile log

- Mode : chaîné, `npm run lint` (ng lint) sur `feat/task-401-delegation-retrait-du-modele-shared` (`b96b12a`).
- Baseline : 0 erreur / 0 avertissement (« All files pass linting ») — **lint clean → no work**.
- Itérations : 0 / 5. Aucun commit.
- Build / tests : ceux de `/develop`, inchangés depuis : build OK, 1 302/1 302.

## E2E log

> ⚠️ **Quarantaine de plus de 14 jours** : E2E-COMPOSE-002 [angular], posée par l'humain le 2026-10-09
> (18 jours), correction attendue par task-350. Le test passe à ce run : sa sortie de quarantaine est
> à décider.
>
> ⚠️ **Divergence à retirer** : E2E-MAILBOX-002 [angular] (task-395), le client est revenu à la version
> du catalogue.

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail, client-mobile et dtos-mss touchés | ✅ verte (jouée) | 47 verts, 0 flaky, 0 rouge, 0 sauté | 7 min 30 s |
| angular | api-mail, client-angular et dtos-mss touchés | ✅ verte (jouée) | 56 verts, 0 flaky, 0 rouge, 0 sauté (dont 1 en quarantaine, passé) | 7 min 47 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ `feat/task-401-delegation-retrait-du-modele-shared` (`0225c9b5`).
  `E2E-DELEG-001` à `007` retirés, et absents des deux suites : parité verte.
- Code testé : api-mail `0225c9b5`, client-mobile `b96b12a`, weda2 `feature/nova-mss-weda-integration` + retrait
  non commité.
- Non-régression HPRIM : `E2E-BIO-001` et `E2E-BIO-003` verts sur les deux voies.
- Quarantaines : E2E-COMPOSE-002 [angular] — passé — correction : task-350.
- Divergences ouvertes : E2E-MAILBOX-002 [angular] — task-395 — **à retirer**.
- Parcours touchés sans spec e2e modifié : aucun (les specs des deux clients ont bougé avec le retrait).
- Démontage : complet pour ce run (ports 5052, 8100, 4200, 3993, 3465, 3143 libres). Deux conteneurs
  `e2e-greenmail-gcgjbrzp` et `e2e-dovecot-kgrndjwd`, arrêtés depuis le 2026-10-14, sont **antérieurs** à ce
  run et laissés en place.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ · divergence (task-395) | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |

**Divergences temporaires ouvertes** (1) :

- E2E-MAILBOX-002 [angular] — le code weda2 de task-378 (écran de panne à l'entrée et son test) n'est pas encore livré sur la branche weda2 ; divergence décidée par l'humain le 2026-10-25 — résorbée par task-395 — **à retirer** : le client est revenu à la version du catalogue

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- `dtos-mss` : https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/pull/51 — label
  `awaiting-human-merge`. **À merger en premier** (contrat 548.0.0 déjà publié).
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/320 — label
  `awaiting-human-merge`.
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/110 — label
  `awaiting-human-merge`.
- `client-angular` : code-only — l'humain gère le commit, le push TFS et l'ouverture de la PR. Branche
  `feature/nova-mss-weda-integration`, 58 fichiers modifiés, non commités (46 modifiés, 12 supprimés), qui
  retirent le contenu des commits TFS `f37bcba2` (Task 398) et `f0b2417b` (Task 399). Exclu :
  `front/.claude/compact-log.txt`.
- **Plan de contrôle** (non commité, **à relire avant le push**, règle d'or 7) : `CLAUDE.md` (règle 14,
  chemin d'`interop-cda`), `agents/po.md`, `conventions/csharp.md`, `conventions/e2e.md`,
  `Docs/audits/delegation-bal-*-20261025.md`.

## Code Review Summary

**Verdict : APPROVED** — 0 point bloquant, 3 remarques non bloquantes.

Le diff est un retrait par revert des commits squashés des tasks 397, 398 et 399. Ce que la revue a vérifié :

- **Revert complet** :
  - plus aucun `shared/` lié à la délégation dans `src/` d'api-mail ;
  - plus aucun identifiant `Delegated*` ni `Delegation*` dans `src/`, `tests/` et `e2e/` ;
  - aucune clé de délégation dans la configuration ;
  - `E2E-DELEG-001` à `007` retirés du catalogue et des deux suites ;
  - banc Dovecot `delegation.conf` retiré.
- **Conflits résolus** : seulement des conflits mécaniques (version DTOs, lock files), plus 4 fichiers où task-389 avait ajouté la détection HPRIM au seul chemin délégué. La détection HPRIM d'une BAL propre (`MedicalSourceParts`) est intacte : les tests d'intégration HPRIM et `E2E-BIO-001` / `E2E-BIO-003` sont verts sur les deux voies.
- **Contrat** : DTOs 548.0.0, soit `develop` moins les champs de task-398 et task-399, et api-mail remonté. Blazor, consommateur NuGet hors périmètre, est en 533.0.0 et n'utilise aucun champ retiré.
- **Tests** : les totaux baissent seulement du nombre de tests de délégation retirés, vérifié par `--list-tests` sur `origin/develop` :
  - api −67, application −89, intégration −42 ;
  - domain −69, infrastructure −6 ;
  - mss-lib −60.
- **Règle 1b** : non applicable. Aucun comportement atteignable par un endpoint ne change pour une BAL sans délégation : le code retiré ne s'exécutait que sous `shared/`.
- **Aucune migration de base**, aucun feature flag.

**Remarques non bloquantes :**

1. ⚠️ **Risque résiduel : un espace `shared/` encore exposé serait réingéré.** Le listage restauré ne parcourt que l'espace personnel. Mais avec un préfixe personnel vide (`(("" "/"))` chez Mailiz), un serveur qui annoncerait encore `shared/` pourrait le faire remonter dans le listage, donc dans la synchronisation, sans garde. C'est le mécanisme de la copie constatée le 2026-10-25 (règle 14, « Pourquoi »). L'humain a vérifié que l'environnement de formation n'expose plus `shared/`. **Avant le merge, confirmer auprès de l'ANS qu'aucune BAL de production ne l'expose encore.** Sinon, ajouter une garde minimale : exclure du listage tout dossier hors de l'espace personnel. Elle serait à écrire dans une task dédiée.
2. ⚠️ **Règle 14 sans mise en œuvre** jusqu'à la délégation par session. C'est voulu et documenté dans CLAUDE.md : aucune fonctionnalité de délégation ne reste livrée.
3. ⚠️ Côté weda2, une vingtaine de fichiers restent en fins de ligne LF dans l'arbre de travail, comme avant le retrait. Git les normalisera au commit (`core.autocrlf=true`).

- Validation `/review` : api-mail build 0 erreur et 0 avertissement, tests 0 échec (domain 195,
  infrastructure 695, api 1 288, application 3 748, intégration 1 011 + 16 ignorés) ; dtos-mss build OK ;
  client-mobile build OK, 1 302/1 302 ; weda2 build OK, `mss-lib` 1 298/1 298.
- Règle 1b (verrou d'intégration) : aucun comportement → test → preuve rouge à établir. Aucun comportement
  atteignable par un endpoint ne change pour une BAL sans délégation.
- Double verrou e2e : `## E2E log` vert (`**E2E : vert**`), deux voies jouées, parité verte.
- DoD : 11/12 cochables par commande, vérifiées. Reste la relecture humaine du plan de contrôle (différée
  au HAG).

## Merged

- Date : 2026-10-27, par `/merge task-401 --i-tested` (validation humaine attestée).
- `dtos-mss` : PR #51 → squash `04b0bee4` ; CI develop verte (run `40574742231`).
- `api-mail` : PR #320 → squash `714b30ba` ; CI develop verte (run `40574771270`).
- `client-mobile` : PR #110 → squash `3db7d1b9` ; CI develop verte (run `40574801768`).
- Branches `feat/task-401-delegation-retrait-du-modele-shared` supprimées (distante et locale) sur les trois dépôts ;
  label `awaiting-human-merge` retiré.
- `client-angular` : managed manually by the human.
- Staging : aucune (task hors run `/forge`).
