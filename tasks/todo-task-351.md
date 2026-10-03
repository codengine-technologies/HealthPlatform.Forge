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
