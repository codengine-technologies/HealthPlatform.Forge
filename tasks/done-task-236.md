# todo-task-236.md — L'outbox de propagation des flags lève dès que le cache d'identifiant est chaud

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune. ⚠️ **Le correctif est déjà sur `develop`** depuis le merge de task-233 (`e296753`, 2026-08-05) — voir « Ce qui reste à faire » ci-dessous.
**Priorité**: **1** — défaut de production **vivant sur `develop`**, en régime établi, sur un
chemin qui touche l'état des messages du praticien. Rien de ce backlog ne passe devant.

> ## ⚠️ Mise à jour du 2026-08-05 — le correctif a été merge avec task-233
>
> La PR #162 (task-233) a été mergée en squash (`e296753`) **avec le commit `357c310` à
> l'intérieur**. Vérifié après synchronisation : `develop` porte la garde
> `DataContextGetterScanTests` **et** zéro emploi du getter `DataContext` dans `src/`. La CI
> de `develop` est **verte**.
>
> **Le remède 1 est donc DÉJÀ FAIT.** L'ordre de merge décrit plus bas est caduc, et la
> duplication qu'il justifiait n'existe plus.
>
> **Ce qui reste à faire, et c'était déjà le cœur de la task :**
>
> 1. **Le test qui échoue sans le correctif** (remède 2) — dépôt exercé **sans contexte
>    injecté**, cache d'identifiant **chaud**, sur les trois méthodes, avec **preuve ROUGE
>    consignée**. Rien ne protège aujourd'hui contre une réintroduction : la garde
>    `DataContextGetterScanTests` interdit l'emploi du *getter*, elle ne prouve pas que le
>    chemin fonctionne cache chaud. Un futur code qui appellerait
>    `GetCurrentUserIdAsync` puis un contexte non résolu par un autre moyen repasserait au
>    travers.
> 2. **Le recensement** des méthodes de `BaseRepository` pouvant retourner sans résoudre le
>    contexte (remède 3) — à consigner même vide.
> 3. **L'arbitrage humain** sur la suppression du getter (remède 4).
>
> Le DOD reste applicable **tel quel** : ses items sur le correctif seront simplement
> constatés déjà satisfaits, ceux sur le test et le recensement restent à produire.

## Objective

Que la propagation des gommettes (lu / non lu / marqué) fonctionne **quand le cache est
chaud**, c'est-à-dire dans l'état normal de l'application. Aujourd'hui elle lève.

## Ce qui a été constaté, et comment

`DataContextGetterScanTests` — la garde d'architecture posée par task-233 — est passée au
**rouge** en fusionnant `develop` dans la branche de task-233. Elle a relevé **8 emplois du
getter `BaseRepository.DataContext`** : **6 dans `PendingActionRepository`**, 2 dans
`MailRepository.GetMailAuditSnapshotAsync`.

### Le mécanisme, établi pas à pas

1. **Le getter lève.** Depuis task-231, `BaseRepository.DataContext` ne résout plus rien :
   il jette `InvalidOperationException` quand aucun contexte n'a été injecté. Le message le
   dit lui-même — *« utiliser GetDataContextAsync() sur le chemin asynchrone »*.
2. **Rien n'est injecté en production.** `MailDataContext` n'est **pas enregistré** dans le
   conteneur. `IPendingActionRepository` est enregistré en `AddScoped`, donc DI ne peut
   choisir que le constructeur `(UserContextInfo, IResilientCacheService, ILogger)` — le
   champ `_dataContext` reste **nul**.
3. **Le getter ne marche qu'après une résolution sur la même instance.**
   `GetDataContextAsync()` mémoïse : `_dataContext ??= await CreateDbContextAsync()`. Tant
   que personne ne l'a appelé sur cette instance, le getter jette.
4. **Et le seul appel qui l'aurait résolu sort tôt.** Les trois méthodes concernées
   commencent par `await GetCurrentUserIdAsync()`. Or cette méthode **retourne
   immédiatement sur un cache Redis chaud** (`user:id:{email}`, cache introduit par
   task-229) — **avant** d'atteindre son `await GetDataContextAsync()`.

### Ce que ça donne à l'exécution

Premier appel après démarrage : cache froid → `GetCurrentUserIdAsync` va en base → le
contexte est résolu → tout fonctionne. **Tous les suivants** : cache chaud → sortie
anticipée → contexte non résolu → **la ligne suivante lève**.

Donc, sur `develop` aujourd'hui, en régime établi :

| Méthode | Effet |
|---|---|
| `TryClaimForProcessingAsync` | lève — **aucune action ne peut être réclamée** |
| `GetPendingFlagActionsAsync` | lève — la file n'est jamais lue |
| `ReleaseClaimAsync` | lève — une action réclamée n'est jamais rendue |
| la suppression après épuisement des tentatives | lève |
| les deux `SaveChangesAsync` | lèvent |
| `MailRepository.GetMailAuditSnapshotAsync` | même motif |

**L'outbox de propagation des flags est hors service.** Le geste du praticien est bien
acquitté en base (c'est le choix de task-230), mais la gommette ne remonte jamais au
serveur IMAP.

### Trois tasks vertes séparément

Le cache d'identifiant (**task-229**), le getter rendu levant (**task-231**), ces emplois du
getter (**task-230**). Chacune verte seule ; le défaut naît de leur composition, et il est
apparu au moment où la troisième a été mergée après la deuxième.

### ⚠️ C'est le symptôme déjà observé, et nous avions nommé une autre cause

Le 2026-08-04, l'humain a marqué trois messages en non-lu et un en marqué depuis
`client-angular`, puis constaté **quatre lignes `PendingActions` restées à `Pending`, aucun
traitement déclenché**. Nous l'avons attribué au défaut `MssRpps` (task-234) — qui était
**bien réel et est corrigé**. Celui-ci en est une **seconde cause, indépendante**, avec le
même symptôme visible. La leçon vaut d'être écrite : **avoir trouvé une cause vraie n'établit
pas qu'elle était la seule.**

### Pourquoi aucun test ne l'attrape

Les tests **injectent** le contexte (`new PendingActionRepository(context, …)`), donc le
getter y fonctionne parfaitement. La production le **résout**. Le harnais est plus permissif
que la production, il valide donc du code qui ne marche pas — **exactement** l'angle mort
de task-235, et la troisième occurrence de la même famille en deux jours.

## Remèdes demandés

### 1. Résoudre le contexte au lieu de le lire sur le getter

Dans chacune des méthodes concernées : `var db = await GetDataContextAsync();` puis employer
`db`. Geste mécanique, sans changement de comportement attendu autre que « ça ne lève plus ».

⚠️ **Un correctif de cette forme existe déjà**, cerné dans le commit **`357c310`** sur la
branche `fix/task-233-patient-file-page-sql-pagination` (PR #162), où il a été écrit parce
que la garde ne pouvait pas rester rouge. Cette task peut le **reprendre tel quel** ; elle
n'a pas à le réinventer. Voir « Ordre de merge ».

### 2. Un test qui échoue AVANT le correctif — et qui ne peut pas tricher

C'est le cœur de la task, davantage que le correctif lui-même.

- Le test doit exercer `PendingActionRepository` **sans lui injecter de contexte**, sur le
  chemin `(UserContextInfo, IResilientCacheService, ILogger)` — celui de la production.
- Avec un cache d'identifiant **chaud** : c'est la condition qui déclenche le défaut. Un
  test à cache froid passe et ne mesure rien.
- **Constater ROUGE** en retirant le correctif : sans cette preuve, on ne sait pas si le
  test regarde le bon endroit. Trois tests de ce cycle se sont révélés sans valeur faute de
  cette vérification.

### 3. Vérifier si le même piège dort ailleurs sur ce chemin

`GetCurrentUserIdAsync` n'est pas la seule méthode qui peut retourner sans résoudre le
contexte. Recenser les méthodes de `BaseRepository` (et de ses dérivés) qui **peuvent sortir
sans résoudre**, et dire lesquelles sont suivies d'un accès au contexte. Le résultat est à
**consigner**, même s'il est vide — c'est ce qui distingue « vérifié » de « pas regardé ».

### 4. Rendre le piège structurellement impossible — à arbitrer, pas à décider seul

Le getter existe encore et compile encore. Deux directions, et le choix est un **arbitrage**
qui doit être écrit :

- **Le supprimer** de la surface accessible aux dépôts (le rendre `private` à
  `BaseRepository`, ou le retirer au profit du seul `GetDataContextAsync`). Le compilateur
  devient la garde ; plus aucun test n'est nécessaire. Coût : les montages qui l'utilisent
  comme setter (tests, fixtures) doivent changer.
- **Le garder** et se reposer sur `DataContextGetterScanTests`. Coût : la garde est un test,
  donc elle peut être désactivée, et elle ne dit rien des dépôts hors `src/`.

⚠️ **Arbitrage humain requis sur ce point.** Le reste de la task est à traiter d'abord ; la
question ne porte que sur celui-ci.

## Ordre de merge

⚠️ **Cette task doit merger AVANT task-233 (PR #162)**, et ce n'est pas une préférence.

task-233 introduit la garde `DataContextGetterScanTests`. Si sa PR mergeait la première, la
garde arriverait sur un `develop` qui **contient encore les 8 emplois** — et la CI de
`develop` passerait au rouge.

Le correctif vit donc **aussi** dans la PR #162 (commit `357c310`), délibérément : task-233
est bloquée par une contre-épreuve au banc non faisable en local, et l'outbox ne doit pas
attendre cette mesure. **La duplication est assumée** — quand cette task merge la première,
la fusion ultérieure de #162 est sans effet sur ces lignes, ou triviale.

*(Alternative écartée : retirer le correctif de #162 par `git revert` du merge. Cela aurait
laissé git croire `develop` déjà fusionné dans cette branche, donc silencieusement
non-réintégré ensuite — un piège pire que la duplication.)*

## Cohérence — bornes explicites

- **Aucun changement de comportement fonctionnel attendu.** La propagation doit faire ce que
  task-230 a décrit, et rien d'autre. Si le correctif révèle un autre défaut, il est
  **signalé** et traité par une task dédiée.
- **Ne pas toucher au cache d'identifiant** (task-229). Il est correct : l'association
  adresse → identifiant est stable. Le défaut n'est pas qu'il existe, c'est que du code
  suppose qu'un appel a résolu le contexte alors qu'il peut ne pas l'avoir fait.
- **Ne pas élargir à `MarkAsFailedAsync`**, dont le défaut connu (jamais rejouée) est
  pré-existant et documenté ailleurs.

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] **Aucun emploi du getter `DataContext` dans `src/`** — `DataContextGetterScanTests` verte
- [ ] **Un test exerce `PendingActionRepository` sans contexte injecté, cache d'identifiant chaud**, et couvre les trois méthodes (réclamation, lecture des actions en attente, libération)
- [ ] **Preuve ROUGE consignée** : en retirant le correctif, ce test échoue — et le message d'échec nomme la cause
- [ ] `MailRepository.GetMailAuditSnapshotAsync` couvert par la même exigence
- [ ] **Recensement écrit** des méthodes de `BaseRepository` pouvant retourner sans résoudre le contexte, et de celles qui sont suivies d'un accès au contexte — même si la liste est vide
- [ ] Décision sur le remède 4 (supprimer le getter, ou le garder sous garde) **écrite avec sa justification**, quelle qu'elle soit
- [ ] Aucune donnée de santé, aucun identifiant national, aucun secret ajouté aux journaux ou aux tests

## Manual Test Plan

```bash
cd Api/Mail
dotnet run --project src/AppHost
```

1. Lancer `client-angular`, se connecter, ouvrir **INBOX** — ce premier appel réchauffe le
   cache `user:id:{email}`, condition du défaut.
2. Passer **trois messages en non-lu** et **en marquer un**.
3. En base, vérifier la table `PendingActions` : les lignes **ne doivent pas rester à
   `Pending`** — elles passent à `Processing` puis disparaissent.
4. **Recharger la boîte depuis un autre client** (ou reconnecter le webmail du fournisseur) :
   les gommettes doivent être **remontées côté serveur IMAP**, pas seulement en base.
5. Vérifier dans les journaux qu'aucune `InvalidOperationException` mentionnant
   « DataContext non résolu » n'apparaît.
6. **Redémarrer l'API et refaire l'étape 2 immédiatement** (cache froid) : le comportement
   doit être identique — c'est ce qui prouve que le correctif ne dépend plus de l'ordre des
   appels.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors vague — correctif de défaut, aucune exigence DSR nouvelle honorée ni retirée
- **Exigences DSR honorées** : aucune nouvelle. ⚠️ Le correctif **restaure** un comportement attendu du couloir : l'état lu/non lu d'un message doit être cohérent entre la plateforme et la boîte MSSanté du praticien
- **INS** : non applicable — aucun traitement d'identité patient modifié
- **Authentification PS** : inchangée — ne touche ni PSC ni e-CPS
- **Habilitations** : inchangées. Le filtre `UserId` des requêtes concernées est **conservé tel quel** : un praticien ne voit que ses propres actions, et le correctif ne doit pas relâcher cette condition
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : ⚠️ **point d'attention réel**. Le défaut fait échouer un chemin d'arrière-plan **silencieusement du point de vue du praticien**. Le correctif doit rester muet sur le **contenu** des messages : aucun sujet, aucune adresse, aucun UID en clair dans un message d'exception ou de journal — seuls des identifiants techniques
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — aucun flux ni stockage nouveau
- **AIPD / impact RGPD** : inchangé — aucun traitement nouveau

## Origine

Ouverte le 2026-08-05 à la demande de l'humain, après que la garde
`DataContextGetterScanTests` — posée par task-233 pour un défaut de la **même famille** —
soit passée au rouge en fusionnant `develop`. Le correctif avait été écrit dans task-233
faute de pouvoir livrer un test rouge ; il est extrait ici pour être revu et mergé pour
lui-même, sans attendre la contre-épreuve au banc qui bloque task-233.


## Branches

- `api-mail` (pushed) : `chore/task-236-outbox-preuve-cache-chaud` —
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/chore/task-236-outbox-preuve-cache-chaud
- `dtos-mss` (pushed) : même nom — **auto-incluse**. Aucun changement de contrat attendu :
  si elle reste vide, aucune PR, suppression manuelle au merge (5e occurrence attendue du
  défaut de cycle).

Préfixe `chore/` : le correctif de production est **déjà sur `develop`** (arrivé avec la
PR #162 de task-233) — ce qui reste est le harnais de preuve, le recensement, et
l'arbitrage sur le getter.

Pré-flight vert sur les six repos mesurables. Dépendances : aucune.


## Develop log

### Remède 2 — le test qui manquait, sur le constructeur de production

`WarmCacheContextResolutionTests` (intégration, vrai PostgreSQL) : quatre tests qui
construisent les dépôts par le **constructeur de production**
(`UserContextInfo, IResilientCacheService, ILogger`) — celui où rien n'est injecté — avec un
**cache d'identifiant chaud** (le substitut répond du premier coup, donc
`GetCurrentUserIdAsync` sort tôt sans avoir résolu le contexte). C'est la combinaison exacte
qui déclenchait le défaut, et elle n'existait **nulle part** dans le harnais : tous les tests
existants injectent le contexte, où le getter fonctionne toujours.

Couvert : les **trois méthodes** de `PendingActionRepository` (réclamation, lecture de la
file, libération) + `MailRepository.GetMailAuditSnapshotAsync`. Le montage emprunte en outre
le **chemin de production intégral** : `CreateDbContextAsync` → provisionnement réel
(CREATE DATABASE + FluentMigrator `MigrateUp`) dans le conteneur — donc les migrations
FluentMigrator **tournent enfin dans un test**, ce que `EnsureCreated` ne fait jamais (angle
mort consigné par task-233). Identité **fictive** unique pour la classe (RPPS
`99700000236`), la base dérivée n'est provisionnée qu'une fois.

### Preuve ROUGE — exigence centrale du DOD, faite

Réintroduction du getter (`var db = DataContext;` à la place de la résolution — l'état exact
d'avant le correctif) → **3 échecs sur 4**, chacun avec le message qui nomme la cause :

```
System.InvalidOperationException : DataContext non résolu — utiliser GetDataContextAsync()
sur le chemin asynchrone (task-231).
   at BaseRepository.get_DataContext() … line 186
```

Correctif restauré → 4/4.

### ⚠️ Portée exacte, sans survente

La preuve ROUGE est **nette pour les trois méthodes de `PendingActionRepository`**. Pour
`GetMailAuditSnapshotAsync`, elle est **impossible en isolation** : `CurrentGenerationAsync`,
appelé en premier, résout déjà le contexte — le correctif de task-233 y était **défensif**
(rien ne garantit cet ordre d'appel), pas la réparation d'un plantage vivant. C'est écrit
dans l'en-tête de la classe de test.

### Remède 3 — le recensement demandé, complet

**Méthodes de `BaseRepository` pouvant retourner sans résoudre le contexte :**

| Méthode / chemin | Sortie sans résolution | Suivi d'un accès contexte ? |
|---|---|---|
| `GetCurrentUserIdAsync` | **oui** — retour immédiat sur cache `user:id:{email}` chaud (task-229) | plus maintenant — les 8 emplois du getter ont été corrigés (task-236/`357c310`), tous les sites résolvent explicitement |
| Constructeur `(UserContextInfo, …)` | par construction — `_dataContext` reste nul | c'est le point de départ du piège |
| `CreateDbContextAsync` (public) | crée **sans mémoïser** dans `_dataContext` | **zéro appelant en production** (seul `PgBouncerTransactionPoolingTests` l'appelle) — piège si un appelant production apparaissait puis lisait le getter |
| `Dispose()` | remet `_dataContext = null` | le getter **se réarme** après dispose — un dépôt réutilisé après dispose relèverait |

**Sorties anticipées sur cache dans les dépôts dérivés** (même famille que
`GetCurrentUserIdAsync`) : `ContactRepository` ×4, `PatientRepository` ×1 (cache patient),
`UserSettingsRepository` ×1. Toutes **sûres aujourd'hui** : leur chemin de miss résout via
`GetDataContextAsync`, et aucun site de `src/` ne lit plus le getter —
`DataContextGetterScanTests` (task-233) le garantit par lecture des sources à chaque build de
la suite api.

**Conclusion du recensement** : le piège structurel restant n'est pas un site existant, c'est
le **getter lui-même** — toujours présent, toujours compilable depuis une méthode d'instance.
D'où le remède 4, qui est un arbitrage humain.

### Validation

Build tests d'intégration 0 erreur (via `--artifacts-path`, l'AppHost verrouillant `src/Api/bin`
— même contournement documenté que task-233) ; `WarmCacheContextResolutionTests` **4/4** ;
preuve ROUGE 3/4 puis restauration 4/4. Suites complètes au moment de `/review`.


### Remède 4 — décision humaine rendue : SUPPRIMER (2026-08-06)

Question posée avec le chiffrage (zéro usage restant du getter/setter, dans `src/` comme dans
les tests) ; réponse humaine : **supprimer**. Appliqué : la propriété publique
`BaseRepository.DataContext` n'existe plus — **le compilateur est désormais la garde**,
impossible à désactiver, là où `DataContextGetterScanTests` restait un test. La garde de scan
est conservée comme ceinture. Justification complète dans le commit et dans le commentaire
laissé à l'emplacement de la propriété.

Le build 0 erreur est la meilleure preuve du chiffrage : rien ne consommait la propriété.


## Simplify log

**Skip propre — rien à simplifier.** Le diff fait 184 lignes sur 2 fichiers : la suppression
de la propriété (nette) et une classe de test déjà structurée autour de trois helpers partagés
(`BuildProductionShapedContext`, `BuildWarmIdentityCache`, `WithProvisioningEnabledAsync`).
La triple construction du dépôt dans les corps de test est de l'idiome xUnit lisible, pas une
règle dupliquée. Poursuivre aurait été du churn cosmétique sur du code écrit dans l'heure.


## Sonar log

### KPIs qualité (baseline → final)

| Métrique | Baseline (task-182, 2026-08-06) | Final (task-236, 2026-08-06) |
|---|---|---|
| Quality Gate (new code) | **ERROR** | **ERROR** |
| `new_violations` | 35 | 36 → 35 (le `S103` de `BaseRepository`, corrigé après relevé) |
| `new_coverage` | 0.0 % (seuil 80) | 0.0 % (seuil 80) |
| `new_security_hotspots_reviewed` | 0.0 % | 0.0 % |

### La mesure qui attribue

**Une** violation dans un fichier touché par cette task : `S103` sur le constructeur de
`BaseRepository` (155 caractères) — **héritée de task-231 et signalée trois fois** dans les
Sonar logs précédents. Corrigée (`7246df0`) : la régler coûtait moins que la re-signaler une
quatrième fois. `WarmCacheContextResolutionTests` : **zéro** finding.

Le reste : la dette héritée cartographiée (outillage k6 26, `AppHost.cs` 3,
`MailServerDiscovery.cs` 2, quatre fichiers à 1). QG rouge sur `new_coverage` = 0 (aucun
rapport importé — seuil inatteignable par construction) et hotspots `Math.random()` de
`journey.js` jamais révisés — **septième signalement**.

### Itérations

**Une seule** : plus aucun finding sur les fichiers de la task après correction.


## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/166 — label `awaiting-human-merge`
- `dtos-mss` : branche auto-incluse **vide**, aucune PR — à supprimer au merge (5e occurrence du défaut de cycle).

## Code Review Summary

**APPROVED**, 0 blocage. La suppression du getter compile du premier coup — confirmation
empirique du chiffrage « zéro consommateur ». Motif `try/finally` sur l'environnement repris
du précédent PgBouncer. Suggestion non bloquante consignée : les deux tests SMTP échouent au
lieu de skipper quand le `.env` est introuvable sous `--artifacts-path` (famille des gardes de
scan, à traiter avec l'outillage).

**Ce que ce cycle ferme** : la boucle ouverte par task-234. Le défaut avait échappé à
3 467 tests parce que le harnais injectait ce que la production résout ; le harnais sait
désormais construire les dépôts comme la production (task-236), échouer sur une erreur
journalisée (task-235), et le getter qui rendait le piège possible **n'existe plus** —
le compilateur est la garde.
