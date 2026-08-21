# todo-task-268.md — Deux chemins de lecture comptent les fils différemment : une conversation initiée par le praticien est visible sur l'un, invisible sur l'autre

**Repos**: api-mail
**Epic**: E009
**Single frontend**: true
**Dependencies**: aucune. **task-194** (`todo`) **préserve délibérément** la
divergence décrite ici, pour rester une pure task de performance — elle ne
tranche pas, elle isole. Celle-ci tranche. Les deux sont livrables dans
n'importe quel ordre ; si task-194 passe d'abord, celle-ci s'applique sur du
code déjà borné, ce qui la rend plus simple.
**Priorité**: **2** — défaut **fonctionnel** visible par le médecin, sur une
fonctionnalité livrée. Ce n'est pas de la performance : un compteur affiche deux
valeurs différentes selon le chemin qui a servi la page.

> **Origine** : constat du 2026-08-20, en instruisant task-194 sur demande
> humaine (« comment es-tu certain de ne pas provoquer de régression ? »).
> Rattaché à **E009** (messagerie sécurisée) et non à E011 : c'est le
> comportement affiché au praticien qui est en cause, pas un coût.

## Objective

Qu'un fil de discussion soit compté **de la même façon** quel que soit le chemin
de lecture qui a servi la page — et que la règle retenue soit celle qui rend
service au médecin.

## Ce qui est établi — état du code au 2026-08-20

Il existe **deux** implémentations du comptage de fils, atteintes par deux
chemins de lecture différents, et **elles ne comptent pas la même chose** :

| | `GetThreadCountsAsync` (`MailRepository.cs:4039`) | `GetMailsByUidsAsync` (`~:1600`, task-247) |
|---|---|---|
| Chemin | `OnlineMailDataProvider` — lecture **IMAP** | lecture servie par la **base** |
| Dossier `Sent` | **exclu** (`!ILike(FolderPath, "Sent")`) sur les deux requêtes | **inclus**, délibérément |
| Justification écrite dans le code | aucune | « Un fil TRAVERSE les dossiers : la racine d'une conversation vit couramment dans `Sent` pendant que les réponses arrivent en `INBOX`. » |

### Le cas concret, et il n'est pas marginal

Une conversation que le **praticien a initiée** : il écrit le premier message
(racine → dossier `Sent`), le correspondant répond (réponse → `INBOX`).

- Chemin **base** : racine comptée + 1 réponse = **2** → le fil s'affiche,
  badge « 2 messages ».
- Chemin **IMAP** : racine exclue, total = 1, **sous le seuil de 2** → le fil
  n'apparaît pas du tout. La réponse s'affiche comme un message isolé.

Le seuil de 2 (`if (totalCount >= 2)`) transforme donc une différence de +1 en
**disparition complète** du fil. Ce n'est pas un écart d'affichage d'un
compteur : c'est un fil qui existe ou n'existe pas selon le chemin.

### Ce qui n'est pas établi, et qu'il faut mesurer

- **Quelle est la fréquence réelle du cas ?** Une conversation initiée par le
  praticien est un geste courant en MSSanté (demande d'avis, envoi d'un compte
  rendu suivi d'une réponse), mais la proportion sur une vraie boîte n'est pas
  chiffrée.
- **Quand chaque chemin sert-il la page ?** `OnlineMailDataProvider` vs lecture
  base : la bascule dépend du mode de connexion (`IConnectionModeService`). Il
  faut établir **quel chemin sert le cas courant** avant de décider lequel
  aligner sur l'autre — aligner le chemin rare sur le chemin courant n'a pas le
  même effet que l'inverse.
- **Y a-t-il d'autres divergences que `Sent` ?** Les deux implémentations ont
  divergé dans le temps ; `Sent` est celle qui a été constatée, pas
  nécessairement la seule. Un inventaire est attendu.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que l'exclusion de `Sent` est un oubli.** Elle est peut-être
  intentionnelle : compter la racine dans `Sent` fait apparaître, dans la boîte
  de réception, des fils dont le premier message n'y est pas. C'est défendable
  dans les deux sens — c'est précisément pourquoi cette US existe au lieu d'un
  correctif direct.
- **Ne pas présumer que l'inverse est un oubli non plus.** task-247 a écrit
  l'inclusion **délibérément**, avec un test de verrouillage
  (`GetMailsByUidsAsyncCountsAThreadWhoseRootLivesInAnotherFolder`). Casser ce
  test sans décision serait annuler un arbitrage antérieur par accident.
- **Ne pas présumer que « unifier » veut dire « supprimer le filtre ».** Les deux
  directions sont ouvertes : inclure `Sent` partout, ou l'exclure partout. La
  seconde ferait **disparaître** des fils aujourd'hui visibles sur le chemin
  base — une régression pour un utilisateur qui les voit déjà.
- **Ne pas présumer que le seuil de 2 est hors sujet.** C'est lui qui amplifie
  l'écart de +1 en disparition. Toute décision sur `Sent` doit énoncer son effet
  combiné avec ce seuil.
- **Ne pas présumer que deux implémentations doivent rester deux.** La vraie
  cause de la divergence est la duplication. Convergence de comportement et
  convergence de code sont deux questions ; la seconde peut être différée, la
  première non.

## Ce que la US doit livrer

1. **Un inventaire des divergences** entre les deux implémentations — pas
   seulement `Sent` : périmètre de dossiers, seuil, déduplication, sensibilité à
   la casse, traitement des racines absentes. Un tableau, pas une prose.
2. **Une règle unique, énoncée en langage métier** : « un fil compte les messages
   qui … , où qu'ils se trouvent, sauf … ». Elle doit être compréhensible par le
   PO, pas seulement par le code.
3. **Les deux chemins appliquent cette règle** et rendent des compteurs
   identiques sur le même jeu de données.
4. **Les cas qui changent d'affichage sont listés nommément**, avec leur sens
   pour le médecin — « avant : ce fil n'apparaissait pas / après : il apparaît
   avec N messages ». Un changement de comportement non listé est un défaut.
5. **Un garde-fou contre la re-divergence** : un test qui exerce **les deux**
   chemins sur le même jeu de données et exige l'égalité des compteurs. C'est le
   seul livrable qui empêche le problème de revenir, et il vaut plus que le
   correctif lui-même.
6. **Si la convergence de code est retenue** (une seule implémentation), elle est
   un bonus, pas l'objectif — l'objectif est l'égalité de comportement, prouvée.

### Hors scope

- **Le coût du comptage** → task-194. Ne pas optimiser ici.
- **Le gating du calcul** → task-266.
- **La correspondance par sous-chaîne sur `References`** (plus correcte par jeton
  au sens RFC 5322) : c'est une troisième question, elle changerait aussi les
  compteurs, et elle mérite sa propre US si elle est confirmée.
- Le regroupement visuel des fils côté client : inchangé, les clients consomment
  les mêmes champs.

## Definition of Done

- [ ] Build passe (`dotnet build HealthPlatform.Api.Mail.sln`, 0 erreur)
- [ ] Tests passent (0 échec, hors flaky pré-existants documentés)
- [ ] **Inventaire des divergences** consigné dans la task, sous forme de tableau,
      établi par lecture des deux implémentations — pas par supposition
- [ ] **La règle retenue est écrite en une phrase métier** dans la task, et
      l'arbitrage qui l'a choisie est daté et attribué
- [ ] Test : sur un même jeu de données, les deux chemins rendent des compteurs
      **identiques** — le garde-fou anti-re-divergence, exerçant réellement les
      deux chemins
- [ ] Test : le cas « racine dans `Sent`, réponse en `INBOX` » a le comportement
      décidé, sur **les deux** chemins
- [ ] Test : le cas « même `MessageId` dans plusieurs dossiers » reste compté en
      lignes (non-régression de task-247, mesurée 3 → 2 à l'époque)
- [ ] Le test de verrouillage de task-247
      (`GetMailsByUidsAsyncCountsAThreadWhoseRootLivesInAnotherFolder`) est
      **toujours vert**, ou son changement est justifié explicitement dans la task
- [ ] **Liste nommée des cas dont l'affichage change**, avec avant/après, dans la
      task et recopiée dans le body de la PR — c'est ce que l'humain valide au HAG
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

1. Démarrer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. Démarrer le front legacy : `cd Client/Angular/front && npm start`
3. Se connecter avec une boîte de test MSSanté de formation.
4. **Construire le cas** : depuis l'application, **envoyer** un message à une
   seconde boîte de test (la racine part dans `Sent`), puis **répondre** depuis
   cette seconde boîte. La première boîte a maintenant une réponse en `INBOX`
   dont la racine est dans son `Sent`.
5. Passer le mode d'affichage sur **« Conversation »**, ouvrir la boîte de
   réception. **Attendu** : le comportement **décidé par la US**, et surtout
   **le même** que celui observé à l'étape 7.
6. Noter ce qui s'affiche : le fil apparaît-il ? avec quel compteur ?
7. **Forcer l'autre chemin de lecture** (bascule du mode de connexion, cf.
   `IConnectionModeService`), recharger la même boîte de réception.
   **Attendu** : **exactement** le même affichage qu'à l'étape 6. C'est le seul
   point qui compte dans ce plan de test.
8. Répéter avec un fil plus long (3 messages, dont la racine dans `Sent`).
9. Contre-épreuve de non-régression : un fil entièrement contenu dans `INBOX`
   doit être compté à l'identique avant/après, sur les deux chemins.

**Données de test** : boîtes de formation MSSanté, aucun patient réel, aucun INS.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : V2 — correctif de cohérence d'affichage sur le volet MSSanté
  existant ; aucune exigence DSR nouvelle
- **Exigences DSR honorées** : MSSanté — restitution cohérente d'un échange de
  messages ; aucune exigence nouvelle adressée
- **INS** : non applicable — le comptage de fils repose sur les en-têtes
  RFC 5322 (`Message-Id`, `In-Reply-To`, `References`), jamais sur l'identité du
  patient
- **Authentification PS** : PSC / e-CPS, niveau eIDAS substantiel — inchangée
- **Habilitations** : inchangées. **Point de vigilance** : la règle retenue ne
  doit **jamais** faire apparaître dans une boîte un message appartenant à une
  autre boîte. Le périmètre reste la base du praticien
- **Interop CI-SIS** : non applicable — aucun format d'échange métier touché
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — cible inchangée
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau, aucun élargissement
  de périmètre de données

## Branches

- `api-mail` (pushed) : fix/task-268-comptage-fils-unifie — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-268-comptage-fils-unifie
- `dtos-mss` (pushed, auto-inclus) : fix/task-268-comptage-fils-unifie — aucune modification attendue (aucun contrat modifié : les clients consomment les mêmes champs)

Préfixe `fix/` : correction d'un défaut fonctionnel — un fil visible sur un
chemin de lecture et invisible sur l'autre.

## Develop log (2026-08-20)

Livré en `5714f7f`.

### ⚠️ Le task file sous-estimait le problème : quatre divergences, pas une

Le garde-fou a été écrit **en premier**, et il a réfuté la lecture d'origine —
il échouait **aussi sur un fil entièrement contenu dans `INBOX`**, alors que la
task n'annonçait qu'une divergence de périmètre de dossiers.

| # | Dimension | Chemin IMAP | Chemin base | Visible par le médecin ? |
|---|---|---|---|---|
| 1 | **`IsThreadRoot`** | la **plus récente** du fil (requête dédiée) | celle **sans parent en base** | **oui** — le client filtre dessus en vue Conversation : la même boîte affichait un **message différent** comme ligne de conversation selon le chemin |
| 2 | **Périmètre de dossiers** | `Sent` **exclu** | `Sent` **inclus** (délibéré, task-247) | **oui** — une conversation initiée par le praticien tombait à 1, sous le seuil de 2 : aucun fil d'un côté, « 2 messages » de l'autre |
| 3 | **`ThreadCount` hors fil** | toujours **1** | `isThreadRoot ? 1 : 0` | marginal (le client traite 0 comme 1) |
| 4 | **`GetThreadAsync`** (dépliage) | — | **troisième** règle : exclure `Sent` **sauf** si le message ouvert y est | **oui** — un fil annoncé « 2 messages » n'en dépliait **qu'un** |

La divergence **1** est la plus grave, et **aucun test ne couvrait `IsThreadRoot`
côté base** (`grep` : 0 occurrence hors de cette task). C'est ce vide qui a
laissé la dérive s'installer sans que personne ne la voie. La **4** n'a été
trouvée qu'en balayant les occurrences résiduelles de l'exclusion après les
premiers correctifs — elle n'était dans aucune lecture initiale.

### La règle retenue — une phrase

> Un fil compte **tous les messages de la boîte du praticien** qui sont sa
> racine ou qui la citent, dans **tous les dossiers** — y compris ceux qu'il a
> envoyés —, **chaque ligne de dossier comptant pour un message**. Un fil existe
> à partir de **deux** messages. La ligne affichée pour un fil est son message
> **le plus récent**, et le déplier montre le **fil entier**.

**Arbitrage, 2026-08-20, forge (retenu par défaut faute d'arbitrage humain
explicite ; réversible)** :

- **« plus récent » plutôt que « racine RFC »** — c'est ce qu'attend une liste de
  conversations (la ligne porte la dernière nouvelle, et le tri par date a un
  sens), et c'est ce que le chemin IMAP implémentait **à dessein**, avec une
  requête dédiée. Le chemin base y arrivait par déduction incidente.
- **`Sent` inclus** — c'est le choix que task-247 avait déjà tranché, avec un
  test de verrouillage et l'argument mesuré : un fil traverse les dossiers, la
  racine d'une conversation initiée par le praticien vit dans `Sent`. L'exclusion
  côté IMAP n'avait ni justification écrite ni test.

### Convergence par construction, pas par coïncidence

- `SelectLatestPerThread` + `BelongsToThread` : **point de passage unique** des
  deux chemins pour la feuille d'affichage et le critère d'appartenance.
- `RootOf` : remplace **trois** copies de la règle de rattachement (comptage,
  mapping, côté IMAP). Trois copies d'une règle sont trois occasions de la voir
  dériver.
- **Zéro requête ajoutée** sur le chemin base : `ThreadLink` porte désormais
  `SentDate`, donc la feuille se calcule sur les lignes **déjà chargées**.
  Réutiliser `GetLatestMessageIdsPerThreadAsync` aurait été plus simple mais
  aurait coûté une requête sur un chemin que task-247 venait d'optimiser.

### Tests — 8, et le garde-fou ne suffit pas

**Garde-fou anti-re-divergence** (le livrable central) : exerce **les deux
chemins sur le même jeu de données** et exige l'égalité de `ThreadCount`,
`IsThreadRoot` et `IsPartOfThread`. Quatre décors : fil enraciné dans `Sent`,
fil intra-`INBOX`, même `MessageId` dans plusieurs dossiers, mono-message.
**Constaté ROUGE avant correctif : 3/4.**

**Trois tests d'ANCRAGE**, parce que le garde-fou seul serait satisfait par deux
implémentations **identiquement fausses** : la feuille est le plus récent ; un
fil enraciné dans `Sent` est compté ; un message hors fil compte pour 1.

**Un test de cohérence compteur/contenu** : déplier un fil rend autant
d'éléments que le compteur annonce — c'est la divergence 4.

### ⚠️ Un piège de décor, trouvé par mutation et pas par raisonnement

`EF.Functions.ILike(m.FolderPath, "Sent")` est une correspondance **exacte**,
sans joker. Mon premier décor nommait le dossier d'envoi `Sent_T268_{suffixe}`
pour l'isolation entre tests — il ne déclenchait donc **jamais** l'exclusion, et
le test « un fil enraciné dans Sent est compté » **passait sur le code
défaillant**. Constaté en réinjectant la mutation : test vert. Le décor nomme
maintenant le dossier exactement `Sent`.

**Corollaire sur le code d'origine, qui vaut d'être noté** : l'exclusion ne
visait que ce **nom littéral**. Une boîte dont le dossier d'envoi s'appelle
`Envoyés` ou `INBOX.Sent` n'était pas concernée. La divergence était donc réelle
mais **plus étroite** qu'elle n'en avait l'air — et son remède reste juste.

**Mutations vérifiées** : sémantique de feuille restaurée → **4 rouges** ;
exclusion de `Sent` restaurée → **2 rouges**.

### Cas dont l'affichage change (exigé au DOD)

| Cas | Avant | Après |
|---|---|---|
| Conversation initiée par le praticien (racine dans un dossier nommé exactement `Sent`), servie par le chemin **IMAP** | aucun fil : la réponse s'affichait seule | fil de **2 messages** |
| Fil quelconque servi par le chemin **base**, en vue Conversation | la ligne affichée était le message le **plus ancien** | la ligne affichée est le **plus récent** |
| Dépliage d'un fil dont un membre est dans `Sent`, message ouvert hors `Sent` | le membre dans `Sent` était **masqué** (compteur > éléments dépliés) | le fil entier s'affiche |
| Message hors de tout fil, chemin base, cas étroit | `ThreadCount` pouvait valoir 0 | vaut 1 |

Aucun autre test existant n'a été cassé par ces changements — ce qui confirme,
en creux, que ces comportements n'étaient **couverts par rien**.

### État des suites

| Suite | Résultat |
|---|---|
| `mss.mail.api.tests` | **665 / 665** ✅ |
| `mss.mail.application.tests` | **2 159 / 2 159** ✅ |
| `mss.mail.domain.tests` | **136 / 136** ✅ |
| `mss.mail.infrastructure.tests` | **464 / 464** ✅ |
| `mss.mail.integration.tests` | **410 / 426** (16 skipped, **0 échec**) ✅ |

Build 0 erreur, **0 avertissement**. Une exécution intermédiaire de la suite
d'intégration a rendu 1 échec non reproduit sur les deux suivantes : c'est
l'instabilité documentée par task-197 (3 exécutions sur 9 rendent 1 à 2 échecs
qui repassent en isolation), pas un effet de cette task.

### Conséquence pour task-194, à reporter

task-194 portait l'instruction « le portage **reproduit l'exclusion `Sent`** du
chemin IMAP », valable tant que la divergence subsistait. Elle est **périmée** :
la sémantique cible est désormais unique, et task-194 doit préserver **celle-ci**.
À amender à la relecture.

## Simplify log (2026-08-20)

Passe qualité sur `api-mail` — `5a2f007`. Le correctif avait laissé du code
mort, et ce code mort tenait **une requête** :

- **Code mort introduit par le correctif** — `hasParentInDb` ne servait qu'à
  décider `IsThreadRoot` (« ce message n'a pas de parent, donc c'est la
  racine »). La feuille d'affichage étant désormais le message le plus récent,
  plus personne ne le lit.
- **Une requête de moins par page de lecture** — `ExistingParentMessageIdSet`
  n'avait que ce consommateur. La requête qui le construisait (`inReplyToIds` →
  `SELECT MessageId WHERE MessageId IN (…)`) disparaît, avec son champ dans
  `BulkMailLookups` et dans le tuple de retour. C'est un gain **non demandé par
  la task**, dans l'esprit de task-247 / task-261 : moins de requêtes sur le
  chemin le plus fréquent de la messagerie. Il ne se serait pas vu sans la passe
  qualité — le code aurait compilé et les tests seraient restés verts.
- **Simplification** — `threadCount > 1 ? leaves.Contains(id) : true` devient
  `threadCount <= 1 || leaves.Contains(id)`. Un ternaire qui rend `true` est un
  `||` qui s'ignore.

Re-validation : build 0 erreur / **0 avertissement** ; api **665/665**,
application **2159/2159**, domain **136/136**, infrastructure **464/464**,
integration **410/426** (16 skipped, 0 échec). `dtos-mss` non touché.

## Sonar log (2026-08-20)

### KPIs qualité — baseline → final

| Condition | Baseline | Final | Seuil | Verdict |
|---|---|---|---|---|
| `new_coverage` | 88,4 % | **88,3 %** | ≥ 80 | ✅ |
| `new_duplicated_lines_density` | 0,058 % | **0,058 %** | ≤ 3 | ✅ |
| `new_security_hotspots_reviewed` | 100 % | **100 %** | 100 | ✅ |
| `new_violations` | 68 | **68** | 0 | ❌ |
| **Quality Gate** | **ERROR** | **ERROR** | — | inchangé |

### Zéro finding introduit — et la provenance est prouvée, pas supposée

Un seul finding porte sur un fichier de la task : `csharpsquid:S138` sur
`MailRepository.cs`, méthode `LoadBulkContentLookupsAsync` (106 lignes > 80).

**Il est pré-existant**, et c'est vérifié sur pièce :

- la méthode est **identique** sur `develop` et sur la branche (même longueur) ;
- `git diff origin/develop -- MailRepository.cs | grep -c LoadBulkContentLookupsAsync`
  renvoie **0** : le diff n'y touche pas.

Elle n'entre dans la fenêtre de new code que parce que les retraits de la passe
qualité, **en amont dans le fichier**, ont décalé sa ligne de déclaration. Sonar
attribue par ligne changée, pas par intention.

**Non corrigée, et c'est un choix** : scinder une méthode de 106 lignes qu'on ne
touche pas, dans une task qui porte sur le comptage des fils, gonflerait le diff
et le risque de revue pour zéro bénéfice à cette US. Elle mérite sa propre passe
— avec les autres `S138` du fichier.

Les 67 autres viennent de tasks **déjà mergées** : `report.py` (22),
`journey-model.js` (14), `journey.js` (7) — harnais des tasks 263/264 — puis
quelques fichiers backend antérieurs. Même phénomène que pour task-265 et
task-216 : la new-code period inclut des tasks mergées, donc la QG peut rougir
sans dette introduite.

### Suites en Release (configuration du scan)

**Les cinq suites entièrement vertes**, 3 834 tests : domain **136/136**,
application **2 159/2 159**, infrastructure **464/464**, api **665/665**,
integration **410/426** (16 skipped, **0 échec**). Ni le flaky PDF ni
l'instabilité d'intégration ne se sont manifestés sur cette exécution.

## Lint Angular log (2026-08-20)

Skip propre — `client-angular` hors `**Repos**` (`api-mail` seul,
`**Single frontend**: true`), aucun fichier Angular touché. Aucune commande,
aucune opération git (mode code-only).

## Lint mobile log (2026-08-20)

Skip propre — `client-mobile` hors périmètre, aucun fichier de `Client/Mobile/`
touché.

## Visual verify log (2026-08-20)

Skip propre — aucun écran `client-mobile` touché (task backend, aucun
`## Stitch design log`).

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/197 — label `awaiting-human-merge`
- `dtos-mss` : aucune modification, pas de PR (branche auto-incluse restée vide)
- Staging : task menée hors run `/forge` — aucune branche staging.

## Code Review Summary

**APPROVED** — 0 blocage, 1 suggestion.

Le correctif tient sa promesse : les quatre divergences sont fermées, et la
convergence est **par construction** (`SelectLatestPerThread`, `BelongsToThread`,
`RootOf` sont des points de passage uniques) et non par coïncidence de deux
implémentations. Le garde-fou anti-re-divergence est le livrable qui empêche le
problème de revenir, et les trois tests d'ancrage compensent sa faiblesse
intrinsèque — il serait satisfait par deux implémentations identiquement fausses.

**Deux défauts trouvés dans mon propre diff en le relisant, et corrigés** :

1. `hasParentInDb` devenu code mort après le changement de sémantique — avec, en
   dessous, une **requête** qui n'avait plus de consommateur. Retirée : gain de
   performance non demandé, sur le chemin de lecture le plus fréquent.
2. L'ordre partiel sur la feuille d'affichage (`SentDate` seule). Rendu total —
   mais **sans revendiquer de preuve** : la mutation ne mord pas, je n'ai pas su
   construire de cas où les deux ordres divergent, et le test le dit.

**Suggestion non bloquante** : la correspondance par **sous-chaîne** sur
`References` est conservée à l'identique. Plus correcte par jeton au sens
RFC 5322, mais la changer modifierait les compteurs — US séparée si confirmé.

### DOD

| Critère | État |
|---|---|
| Build 0 erreur, tests 0 échec | ✅ (0 avertissement aussi) |
| Inventaire des divergences en tableau | ✅ 4 dimensions, établi par lecture des deux implémentations |
| Règle retenue en une phrase métier + arbitrage daté | ✅ |
| Test : les deux chemins rendent des compteurs identiques | ✅ garde-fou, 5 décors |
| Test : cas « racine dans `Sent` » sur les deux chemins | ✅ |
| Test : même `MessageId` dans plusieurs dossiers compté en lignes | ✅ (non-régression task-247) |
| Test de verrouillage de task-247 toujours vert | ✅ `GetMailsByUidsAsyncCountsAThreadWhoseRootLivesInAnotherFolder` |
| Liste nommée des cas dont l'affichage change | ✅ 4 cas, dans la task et dans la PR |
| Aucune donnée de santé dans les logs | ✅ aucun log ajouté |
