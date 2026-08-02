# todo-task-218.md — Retirer `ICacheService` du SDK : un cache sans budget de temps, sans disjoncteur et sans tolérance à la panne, que 58 appels traversent

**Repos**: sdk, api-mail, client-blazor
**Epic**: E015
**Single frontend**: false
**Dependencies**: **task-217 (doit être mergée)** — elle marque `ICacheService`
`[Obsolete]`, ajoute les tests du SDK et publie le paquet. Sans elle, cette US
migrerait vers un `IResilientCacheService` dont rien ne garantit encore le
budget de temps.
**Priorité**: **2** — les deux chemins chauds identifiés en juillet
(`UserSettingsRepository`, `SearchHistoryService`) ont déjà été sortis par le
contournement de task-205, et le chemin mesuré en août est traité par task-217.
Ce qui reste est bloquant mais moins sollicité.

> **Seconde moitié d'un chantier découpé.** L'inventaire complet donnait 64
> appels sur 52 fichiers, au-dessus du plafond de la règle 5. task-217 a pris le
> chemin mesuré (6 appels) ; celle-ci prend le reste (58) et **supprime**
> l'interface.

## Objective

Qu'il ne reste qu'**une seule** abstraction de cache dans le SDK, et qu'aucune
I/O synchrone n'y subsiste.

## Le défaut

`ICacheService` (`Get<T>` / `Set<T>` / `Remove`) descend sur
`IDistributedCache.GetString` / `SetString` / `Remove`, donc sur
`StackExchange.Redis.RedisBase.ExecuteSync` : un aller-retour réseau
**bloquant** sur un thread du pool, **sans budget de temps** et **sans
disjoncteur**.

Deux symptômes de son inadéquation, déjà dans le code :

- api-mail a dû écrire `SafeCacheExtensions` (task-074) pour l'entourer de
  `try/catch` — l'interface ne tolère pas la panne, il a fallu la lui ajouter
  par-dessus ;
- task-205 a dû **contourner** le SDK en descendant sur `IDistributedCache`
  pour obtenir de l'asynchrone sur deux chemins chauds.

`IResilientCacheService` fait déjà tout ce que ces deux rustines apportent :
async, budget de 500 ms, disjoncteur, compteurs de santé.

## Périmètre chiffré

| Cible | Volume |
|---|---|
| Appels `Get` / `Set` / `Remove` dans api-mail | **58** |
| Fichiers de production api-mail | ~26 — dont `ImapService`, `ImapFolderService` (la moitié des appels), `BaseRepository` et ~15 dépôts |
| Fichiers de tests api-mail référençant `ICacheService` | **26** |
| client-blazor | **1** ligne d'enregistrement DI (`Src/Shell/Extensions/ServiceCollectionExtensions.cs:20`) |

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que la migration est un simple remplacement de type.**
  `ICacheService` **lève** en cas de panne Redis ; `IResilientCacheService`
  **avale et retourne `default`**. Un appelant qui distinguait « erreur » de
  « absent » par un `try/catch` change de sémantique. Recenser ces appelants
  **avant** de convertir, et écrire pour chacun que l'équivalence est vraie —
  ou traiter le cas.
- **Ne pas présumer que `default` vaut « absent » partout.** Pour un cache c'est
  presque toujours vrai, mais `CrlValidationService` et `OcspValidationService`
  cachent des éléments de **validation de certificat** : un « absent » silencieux
  y déclenche une revalidation, pas une acceptation par défaut. À **vérifier**,
  parce que l'inverse serait un défaut de sécurité.
- **Ne pas présumer que l'asynchronisation s'arrête au site d'appel.**
  `BaseRepository` expose `protected ICacheService CacheService` : le changement
  remonte dans une quinzaine de dépôts, et rendre `async` une méthode
  aujourd'hui synchrone se propage à ses appelants. Mesurer la cascade avant de
  commencer ; si elle déborde le plafond de la règle 5, **re-découper** plutôt
  que de livrer une PR de 80 fichiers.
- **Ne pas présumer que le contournement de task-205 se supprime sans garde.**
  Les variantes `Safe*Async` de `SafeCacheExtensions` sérialisent, d'après leur
  commentaire, « exactement » comme le SDK (JSON par défaut, valeur en string).
  **À prouver par un test** : une entrée écrite par une voie doit rester lisible
  par l'autre, sinon la bascule invalide silencieusement le cache en production.

## Contenu attendu

1. **SDK** : `ICacheService` et `CacheService` **supprimés** ;
   `ServiceCollectionExtensions.AddSdk` mis en cohérence. Publication + bump.
2. **api-mail** : 58 appels migrés vers `IResilientCacheService`, `BaseRepository`
   et les dépôts adaptés, et **retrait** des variantes redondantes de
   `SafeCacheExtensions` (`SafeGet` / `SafeSet` / `SafeRemove` et leurs
   équivalents `Async`) devenues sans objet.
3. **client-blazor** : enregistrement DI mis en cohérence, build + tests verts.
4. **Un test par appelant dont la sémantique d'erreur change** — c'est le risque
   principal de cette US, pas la compilation.
5. **Compatibilité de sérialisation** prouvée par test.

## Hors scope

- `IMarkdownService.ToHtml` — calculatoire, reste synchrone (déjà tranché par
  task-217).
- Le réglage des valeurs du disjoncteur.

## Definition of Done

- [ ] Build passes (0 erreur) et tests verts sur **les trois repos**
- [ ] Plus aucune occurrence d'`ICacheService` dans les trois repos
- [ ] **Aucune** I/O synchrone ne subsiste dans le SDK — garde par test
- [ ] Chaque appelant dont la sémantique d'erreur change est **nommé** dans le
      `## Develop log`, avec la raison pour laquelle l'équivalence tient
- [ ] `CrlValidationService` et `OcspValidationService` : test prouvant qu'une
      panne de cache déclenche une **revalidation**, jamais une acceptation
- [ ] Test de compatibilité de sérialisation ancienne voie → nouvelle voie
- [ ] `Directory.Packages.props` bumpé dans api-mail **et** client-blazor
- [ ] Tests **constatés RED avant le correctif** (preuve dans le `## Develop log`)

### Dû au banc (ne bloque pas la PR, bloque la clôture de l'US)

- [ ] Tir 500 praticiens : aucun thread applicatif parqué dans `ExecuteSync`
      (contrôle par pile, sur le modèle de task-205)

## Manual Test Plan

```bash
cd Api/Mail && dotnet run --project src/AppHost
```

**Écran** : la messagerie — ouvrir la liste des dossiers, un message, lancer une
recherche.

**Ce que l'humain doit voir** :
- comportement inchangé, Redis debout ;
- après `docker stop` du conteneur Redis : l'application **continue de
  fonctionner** (repli sur la source), sans attente de plusieurs secondes ;
- ⚠️ **le contrôle qui compte** : ouvrir un message dont le certificat est à
  valider pendant que Redis est arrêté — la validation doit être **refaite**,
  jamais court-circuitée en « valide ».

**Blazor** : `cd Client/Blazor && dotnet run` — l'application démarre.

**Données de test** : compte de développement, aucune donnée de santé réelle.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville — messagerie MSSanté du praticien.
- **Vague Ségur** : hors vague — robustesse interne.
- **Exigences DSR honorées** : aucune nouvelle.
- **INS** : non manipulée. **Authentification PS** : inchangée.
- **Habilitations** : ⚠️ les clés de cache portent l'email du praticien. Le
  cloisonnement par clé doit être **conservé à l'identique** — une clé dont le
  praticien disparaîtrait ferait servir le message d'un praticien à un autre.
  Test de garde exigé.
- ⚠️ **Sécurité — le point dur de cette US** : `CrlValidationService` et
  `OcspValidationService` cachent des éléments de validation de certificat. Le
  passage d'une sémantique « lève » à une sémantique « retourne `default` » ne
  doit **jamais** transformer une panne de cache en acceptation d'un certificat.
- **Interop CI-SIS** : non applicable.
- **Tracé PGSSI-S** : aucun évènement métier touché.
- **Hébergement HDS** : non applicable.
- **AIPD / impact RGPD** : inchangé. Durées de conservation du cache inchangées.
