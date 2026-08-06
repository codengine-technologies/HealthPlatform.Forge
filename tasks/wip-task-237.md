# todo-task-237.md — Le scope de tâche de fond n'est jamais créé pendant les tests : câbler la file et prouver que le travail a lieu

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-235 — livre le filet à erreurs journalisées, `MssRpps` et la chaîne
serveur dans les fixtures. **Ses deux premiers acquis sont des prérequis stricts** : sans eux,
l'assertion centrale de cette US ne discrimine rien.
**Priorité**: **2** — aucun apport au médecin, mais c'est la moitié manquante du filet. Ce qui
est livré attrape ce que le chemin de fond journalise **quand il est emprunté** ; rien ne le
fait emprunter.

> ⚠️ **Aucun impact produit.** Cette US ne touche que le harnais de test. Si le câblage révèle
> un défaut de production, il est **signalé** et traité par une task dédiée — cette US livre le
> filet, pas les poissons qu'il attrape.

## Objective

Que les tests d'intégration **créent réellement** le scope de tâche de fond, et prouvent que le
travail y a **eu lieu** — pas que la requête a répondu 200.

## Ce qui est établi, et par qui

`IBackgroundTaskQueue` **n'est enregistrée dans aucune fixture d'intégration**
(`ImapServicesFixture`, `UseCaseFixture`). Les services de production la prennent en paramètre
**optionnel** : elle vaut donc `null` et le code emprunte son **repli en ligne**, qui utilise le
contexte **de la requête** — complet. Trace, dans les journaux de la suite elle-même :

```
[FlagChange] No background queue wired — propagating MarkUnread inline for INBOX/4277
```

**Le scope de fond n'est donc jamais créé pendant les tests d'intégration.** C'est le troisième
angle mort identifié par task-235, et le seul qu'elle n'a pas traité.

### Pourquoi c'est maintenant faisable, alors que ça ne l'était pas

task-235 a posé les deux prérequis, et il a fallu les deux :

1. **`MssRpps`** dans les fixtures — sans lui, requête et tâche de fond dérivent le **même** nom
   de base et l'écart est structurellement inobservable ;
2. **`ConnectionStringServer`** — sans elle, tout scope construisant son propre contexte tombait
   sur un **hôte nul**. C'est ce que le filet a révélé : six tests rouges sur
   `Error creating DbContext … Parameter 'Host'`, la jambe de durabilité morte en silence.

Tant que ces deux manques tenaient, câbler la file n'aurait produit qu'une avalanche d'erreurs
sans rapport avec le défaut cherché.

## Remèdes demandés

### 1. Câbler `IBackgroundTaskQueue` — avec un exécuteur **synchrone à la demande**

- Enregistrer la file **et** un exécuteur de test qui déroule les éléments **quand le test le
  demande**, pas un hôte qui tourne en tâche de fond.
- ⚠️ **Aucune attente, aucun sommeil, aucune scrutation.** `Task.Delay`, `Thread.Sleep` et les
  boucles d'attente sont **interdits** : une suite lente et intermittente est une suite qu'on
  ignore — précisément le travers que task-235 corrigeait.
- L'exécuteur doit **propager les exceptions** du travail de fond au test qui le déroule.
  Un exécuteur qui les avale reproduirait l'angle mort qu'on referme.

### 2. Un test par chemin de fond, assertant l'**effet**

Au moins un pour chacun : **enrichissement asynchrone**, **réconciliation de dossiers**,
**propagation de flags**. L'assertion porte sur l'effet observable — une ligne écrite, un flag
posé, un cache invalidé — **jamais** sur un code HTTP.

### 3. L'assertion qui aurait attrapé task-234

**Comparer le nom de base employé par la tâche de fond à celui de la requête.** Comparaison du
**nom de base**, pas de la liste des champs recopiés : une liste de champs se vérifie déjà par
réflexion (task-234), et c'est le nom de base qui décide où les données vont réellement.

Cet item était au DOD de task-235 et n'a pas été écrit — il est devenu **écrivable** par elle.

### 4. Faire disparaître la ligne qui dit l'angle mort

Le journal `No background queue wired` ne doit plus apparaître pour les chemins désormais
câblés. C'est un critère observable, et le plus simple à vérifier.

## Cohérence — bornes explicites

- **Aucun code de production modifié.** Le paramètre optionnel de la file **reste** optionnel :
  le rendre obligatoire serait un changement de production, donc une autre task.
- Le remède 1 peut faire **échouer des tests aujourd'hui verts** — c'est son objet, comme pour
  task-235. Chaque échec est soit un vrai défaut (task dédiée), soit une exemption justifiée.
  **Ni l'un ni l'autre ne se règle en désactivant le câblage.**
- Ne pas élargir l'adoption du filet de task-235 aux dix classes restantes : c'est un travail
  distinct, sur des fixtures où le fournisseur n'est pas branché.

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] `IBackgroundTaskQueue` **câblée** dans `ImapServicesFixture` et `UseCaseFixture`
- [ ] **Exécution déterministe** : aucun `Task.Delay`, aucun `Thread.Sleep`, aucune boucle d'attente dans les tests — vérifié par recherche
- [ ] L'exécuteur de test **propage les exceptions** du travail de fond — test le prouvant
- [ ] **Un test par chemin de fond** (enrichissement asynchrone, réconciliation de dossiers, propagation de flags) assertant l'**effet**, pas le code HTTP
- [ ] **Un test compare le nom de base employé par la tâche de fond à celui de la requête**
- [ ] **Preuve ROUGE** : en réintroduisant l'oubli de `MssRpps` dans un chemin de fond, ce test échoue en **nommant l'écart de base**
- [ ] Le journal `No background queue wired` **n'apparaît plus** pour les chemins câblés — vérifié dans la sortie de la suite
- [ ] La suite d'intégration **ne s'est pas allongée** de façon notable (référence : ~2 min 45 s pour 364 tests au 2026-08-05)
- [ ] Aucun secret ni donnée de santé ajouté au harnais
- [ ] Tout défaut de production révélé est **signalé dans le task file**, non corrigé ici

## Manual Test Plan

- `dotnet test tests/mss.mail.integration.tests/mss.mail.integration.tests.csproj` : suite verte,
  durée comparable à la référence ci-dessus
- Chercher `No background queue wired` dans la sortie : **absent** pour les chemins câblés
- Réintroduire volontairement l'oubli de `MssRpps` dans un chemin de fond et vérifier qu'un test
  échoue **en nommant l'écart de base**
- Retirer volontairement l'exécuteur du câblage et vérifier que les tests des chemins de fond
  échouent — sans quoi ils ne mesuraient pas le travail de fond

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — outillage de test interne, aucune exigence DSR nouvelle honorée ni retirée
- **Exigences DSR honorées** : non applicable — aucun changement de périmètre fonctionnel
- **INS** : non applicable — aucun traitement d'identité modifié. Le RPPS de test reste **fictif**
- **Authentification PS** : inchangée — ne touche ni PSC ni e-CPS
- **Habilitations** : non applicable — aucune règle d'accès modifiée
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé. ⚠️ Le travail de fond déroulé en test **écrit en base** : il doit
  rester cantonné à la base du conteneur de test, et l'affichage d'un échec ne doit recopier
  aucun contenu de message MSSanté
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — aucun flux ni stockage nouveau
- **AIPD / impact RGPD** : inchangé. La boîte de test reste un compte dédié, hors données réelles

## Origine

Découpée de **task-235** le 2026-08-06, sur décision humaine. task-235 a livré ses remèdes 1
et 3 (le filet à erreurs journalisées, `MssRpps`, la chaîne serveur) et **n'a pas entamé** son
remède 2. Le découpage a été retenu parce que le filet livré attrape déjà de vrais défauts et
n'avait pas à attendre : le laisser sur une branche prolongeait l'aveuglement qui a laissé
passer task-234, task-233 et task-236.


## Branches

- `api-mail` (pushed) : `chore/task-237-cabler-file-taches-de-fond` —
  https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/chore/task-237-cabler-file-taches-de-fond
- `dtos-mss` (pushed) : même nom — **auto-incluse**, aucun changement de contrat attendu
  (US harnais de test pur) ; si vide, aucune PR, suppression manuelle au merge (6e occurrence
  attendue du défaut de cycle).

Pré-flight vert sur les six repos mesurables. Dépendance task-235 : **archivée (mergée)** —
satisfaite. Acquis disponibles depuis sa rédaction : task-236 a aussi supprimé le getter
`DataContext` (compilateur = garde) et fait tourner les migrations FluentMigrator dans un
test.
