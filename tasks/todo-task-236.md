# todo-task-236.md — L'outbox de propagation des flags lève dès que le cache d'identifiant est chaud

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune. ⚠️ **À merger AVANT task-233** — voir « Ordre de merge » ci-dessous.
**Priorité**: **1** — défaut de production **vivant sur `develop`**, en régime établi, sur un
chemin qui touche l'état des messages du praticien. Rien de ce backlog ne passe devant.

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
