# todo-task-351.md — Étape 2 d'AUD-42 : supprimer du contrat les champs serveur que plus personne ne lit

**Repos**: dtos-mss, api-mail, client-blazor, client-angular
**Dependencies**: task-348 **mergée et déployée**, et **tous les fronts déployés à jour** (Blazor, Angular TFS) — voir « Condition de lancement »
**Epic**: E009
**Priorité**: 4 — dette de contrat, sans effet utilisateur ; la faille est fermée par task-348.

> **Origine.** task-348 (AUD-42) a fait résoudre le serveur de messagerie par le seul serveur.
> Elle a gardé `UserSettingsDto.ImapServerConfig` / `SmtpServerConfig` marqués `[Obsolete]`,
> parce que `client-angular` est déployé par l'humain via TFS, à son rythme : un ancien front
> envoie encore ces champs, et api-mail les ignore (mis à `null`, réponse 200).

> **Condition de lancement — arbitrage humain requis.** Ne lancer que quand l'humain confirme
> que **tous** les fronts déployés (Blazor et Angular, toutes instances) sont au niveau de
> task-348 ou plus. Le risque technique est faible : un champ inconnu envoyé par un ancien front
> est ignoré par System.Text.Json, et un ancien front qui lit `imapServerConfig` reçoit déjà
> `null` depuis task-348. La condition reste posée par prudence, et c'est l'humain qui la lève.

## Objective

Retirer du contrat, puis de chaque consommateur, les deux champs serveur que task-348 a rendus
inertes, et nettoyer les valeurs résiduelles en base.

## Périmètre

1. `dtos-mss` : supprimer `UserSettingsDto.ImapServerConfig` / `SmtpServerConfig` et leur
   constante `ServerSelectionRetired`. Publication NuGet, bump d'`api-mail` et `client-blazor`.
2. `api-mail` : supprimer `SettingsController.DropServerSelection` (devenu sans objet) et le
   `#pragma warning disable CS0618` qui l'accompagne ; les tests qui prouvaient le vidage
   deviennent des tests de non-régression « `GET /settings` ne contient aucune propriété
   serveur » (JSON brut).
3. Base : script ou migration qui retire `imapServerConfig` / `smtpServerConfig` du JSON des
   réglages déjà stockés (le blob est remplacé en bloc à chaque enregistrement ; vérifier le
   format réel avant d'écrire la migration, règle 7c).
4. `client-blazor` : rien à retirer côté écran (fait par task-348) ; recompiler contre le
   nouveau DTO.
5. `client-angular` : retirer `imapServerConfig` / `smtpServerConfig` de
   `user-settings.model.ts` et la fonction `withoutServerSelection` de
   `mss-settings.component.ts` (avec ses tests), devenue sans objet.

## Hors périmètre

- `MailServerConfigDto` reste : `MailServerInfoDto` (réponse de `GET /settings/mail-server`)
  l'utilise.
- `client-mobile` : n'a jamais porté ces champs.

## Definition of Done

- [ ] Build passes (0 errors) — dtos-mss, api-mail, client-blazor, client-angular
- [ ] Tests pass (0 failures) — hors rouges pré-existants identifiés sur `develop`
- [ ] `grep -rn "ImapServerConfig\|SmtpServerConfig" Dtos Api/Mail/src Client/Blazor/Src` ne renvoie rien
- [ ] `grep -rn "imapServerConfig\|smtpServerConfig\|withoutServerSelection" Client/Angular/front/libs/mss/src` ne renvoie rien
- [ ] Test d'intégration `GET /settings` sur des réglages stockés AVANT la migration (JSON porteur des deux champs) : la réponse ne contient aucune propriété serveur, lue dans le JSON brut — vu rouge (règle 1b)
- [ ] Migration des réglages : relue, sans opération fantôme, « pending changes » vide (règle 7c)
- [ ] `dtos-mss` publié, consommateurs .NET bumpés

## Manual Test Plan

1. `cd Api/Mail && dotnet run --project src/AppHost`, client Blazor et client Angular connectés
   avec une boîte de test sur `medecin.formation.mssante.fr`.
2. Blazor → Paramètres : l'encart du serveur s'affiche comme avant ; modifier la signature et
   enregistrer → succès.
3. Angular → Paramètres : même vérification.
4. `GET /api/v1/settings/getsettings` (Swagger) → la réponse ne contient ni `imapServerConfig`
   ni `smtpServerConfig`.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville, biologie
- **Vague Ségur** : V2
- **Exigences DSR honorées** : non applicable — nettoyage de contrat
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable
- **Consentement patient** : non applicable
- **Référentiels métier** : non applicable
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : non applicable

## Branches

> **Condition de lancement levée par l'humain** : `/start 351` lancé le 2026-10-04, après l'exposé de la condition « tous les fronts déployés au niveau de task-348 ». Périmètre inchangé, migration des réglages stockés comprise (aucune décision contraire).

- `dtos-mss` (pushed, branche paresseuse) : `chore/task-351-retrait-champs-serveur`, créée par `/develop` au moment de toucher le contrat
- `api-mail` (pushed) : chore/task-351-retrait-champs-serveur — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/chore/task-351-retrait-champs-serveur
- `client-blazor` (pushed) : chore/task-351-retrait-champs-serveur — https://github.com/codengine-technologies/HealthPlatform.Client/tree/chore/task-351-retrait-champs-serveur
- `client-angular` (code-only) : la forge écrit sur la branche active de `Client/Angular/` (`feature/nova-rewriting-mss` au /start). ⚠️ Les fichiers de task-353 n'y sont **pas encore commités** ; ceux de task-351 (`user-settings.model.ts`, `mss-settings.component.*`) sont distincts et seront listés à part. L'humain gère la branche, le commit, le push et la PR TFS.

## Timings

*(généré par `tools/timing/report.sh --task task-351 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 27 s | — | — | — | — |
| /develop | ok | 9 min 40 s | 2 (31 s) | 4 (4 min 26 s) | — | api-mail 1B/2T, dtos-mss 1B/0T, client-blazor 0B/1T, client-angular 0B/1T |
| **Total cycle** | | **10 min 08 s** | **2 (31 s)** | **4 (4 min 26 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : nuget-wait ×1 (10 s)

## Develop log

**Ordre** : dtos-mss → api-mail → client-blazor → client-angular (code-only).

### Ce qui a été fait
- **dtos-mss** (`chore/task-351-retrait-champs-serveur`, branche paresseuse créée ici) :
  - suppression de `UserSettingsDto.ImapServerConfig` / `SmtpServerConfig` et de la constante `ServerSelectionRetired` ;
  - `MailServerConfigDto` reste (utilisé par `MailServerInfoDto`) ;
  - publication **517.0.0** par la CI (run 37210303170, vert). Un second push, qui ne fait que reformuler un commentaire, republie en 518 avec la même API ; les consommateurs restent en 517.
- **api-mail** :
  - `Dtos.Mss` 517.0.0, avec les `packages.lock.json` ;
  - `SettingsController.DropServerSelection` supprimé, ainsi que son `#pragma warning disable CS0618` ;
  - les deux tests unitaires qui prouvaient le vidage sont retirés (champs inexistants), le comportement est prouvé en intégration sur le JSON brut ;
  - migration FluentMigrator **20261004120000** `RetireServerSelectionFromSettings` : un `UPDATE` qui retire les deux clés du JSON des réglages stockés (`jsonb - 'imapServerConfig' - 'smtpServerConfig'`), limité aux lignes qui les portent. Sa descente est volontairement vide.
- **client-blazor** : `Dtos.Mss` 517.0.0, recompilé. Aucun code ne nommait les champs (déjà retiré par task-348).
- **client-angular** (code-only, non commité) :
  - `imapServerConfig` / `smtpServerConfig` retirés de `UserSettingsDto` ;
  - `withoutServerSelection` et son test retirés de `mss-settings.component.ts` ; l'enregistrement envoie `this.settings()` ;
  - le spec n'emploie plus de réglages « porteurs d'un serveur » (`storedSettings`).

### Tests rouges d'abord (règle 1b)

| Comportement | Test | Preuve du rouge |
|---|---|---|
| `GET /settings` sur des réglages stockés avant task-348 (JSON porteur des deux champs) : aucune propriété serveur dans la réponse, lue en JSON brut | `SettingsMailServerEndpointIntegrationTests.GetSettings_StoredWithTheRetiredServerFields_ReturnsNoServerProperty` | rouge sur le code d'avant : `"imapServerConfig":null` présent |
| Enregistrer avec un serveur : accepté, rien n'est stocké ni rendu | `PostingAServer_IsAccepted_ButNeverStoredNorReturned_…` (adapté au JSON brut) | rouge sur le code d'avant (même cause) |
| Migration : les deux clés partent, le reste du JSON et les autres lignes restent intacts | `RetireServerSelectionMigrationTests.MigratingStoredSettings_RemovesTheServerKeys_AndKeepsEverythingElse` (coureur de production rejoué jusqu'à 20261002120000, puis lignes déposées, puis migration) | rouge sans la migration : clés présentes |

### Règle 7c (migration)
- Migration relue : elle fait ce qui est prévu.
- Aucune opération fantôme : un seul `UPDATE`, filtré.
- Pas de fichier compagnon (FluentMigrator : ni `.Designer` ni snapshot).
- « Pending changes » sans objet : le schéma n'est pas géré par des migrations EF.
- Le JSON visé a été écrit par le sérialiseur, donc la conversion en `jsonb` ne peut pas échouer.

### DOD (greps)
- `grep -rn "ImapServerConfig\|SmtpServerConfig" Dtos Api/Mail/src Client/Blazor/Src` : **0** (le commentaire du DTO a été reformulé).
- `grep -rn "imapServerConfig\|smtpServerConfig\|withoutServerSelection" Client/Angular/front/libs/mss/src` : **0**.

### Passe qualité §Q
Faite en revue directe : le diff consiste presque entièrement en suppressions, rien à simplifier.

### Validation
- api-mail : domain 190, infrastructure 683, api 1 176, application 3 433, intégration 803 (+16 ignorés).
- Blazor : 423 (+2 ignorés).
- Angular `libs/mss` : 581.
- dtos-mss : build OK.

