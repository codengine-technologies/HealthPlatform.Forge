# todo-task-189.md — Durcissement de la surface HTTP : purge destructive non gardée, corps invalide en 500, GET qui écrit

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe surface HTTP).
> Findings vérifiés sur pièces par le PO.

## Objective

Corriger quatre défauts de la surface HTTP qui rendent l'API destructive,
imprévisible ou non conforme au contrat d'erreur du projet (règle 12, RFC 7807).

**US backend-only (justification)** : contrôleurs et pipeline HTTP. Les codes de
retour se corrigent (500 → 400), ce qui va dans le sens de ce que les frontends
attendent déjà.

### Preuve (état actuel du code)

**1. Purge destructive accessible à tout praticien authentifié** —
`src/Api/Controllers/V1/MailMaintenanceController.cs:105-126` :
```csharp
[HttpDelete("purge-mails")]
public async Task<IActionResult> PurgeMailsAsync()
{
    …
    await context.Database.ExecuteSqlRawAsync("TRUNCATE TABLE \"MailMedicalDocuments\" CASCADE");
    … 6 TRUNCATE au total, dont "Mails" RESTART IDENTITY CASCADE
```
Le commentaire du contrôleur dit « admin-only diagnostics … intended for non-prod
environments » — mais **rien ne l'applique** : vérifié, aucun attribut `[Authorize]`
ni `[AllowAnonymous]` sur ce contrôleur, aucun contrôle d'environnement, aucun
paramètre de confirmation. Le seul rempart est la politique globale
(`src/Api/Program.cs:129-132` : `RequireAuthenticatedUser`) — donc **n'importe quel
praticien authentifié** peut vider irréversiblement sa base mail (contenus
enrichis, documents CDA, accusés de biologie, liens patients).

**2. Corps de requête invalide ⇒ 500 au lieu de 400** —
`src/Api/Program.cs:57` : `options.SuppressModelStateInvalidFilter = true`. Un corps
qui échoue au binding ne produit donc pas le 400 automatique : l'action s'exécute
avec le paramètre à **`null`**. Douze actions déréférencent le modèle avant (ou
sans) vérifier `ModelState` : `AiController.cs:35,81,95,111` ;
`AiDiagnosticsController.cs:64,361-362` ; `SearchController.cs:63,131` ;
`AiChatController.cs:53` ; `PatientsController.cs:168-169` ;
`MailController.cs:294,340` ; `SignatureController.cs:51` ;
`MailTemplateController.cs:55,80`.
C'est exactement la forme du bug déjà traité côté mobile (task-168 : `"id":""`
invalide pour un `Guid` ⇒ corps lié à `null` ⇒ NRE). Le patron correct existe déjà
dans le repo : `ContactController.cs:26-36` garde chaque corps via `RequireBody`.

**3. Une écriture exposée en GET** —
`src/Api/Controllers/V1/SettingsController.cs:41-42` : l'action porte à la fois
`[HttpPost]` et `[HttpGet("settings")]`. Or elle **remplace en bloc** les
paramètres du praticien. Une opération d'écriture est donc joignable par une méthode
que le contrat HTTP déclare sûre et idempotente — éligible au préchargement et au
rejeu par les navigateurs et les proxys. La lecture a sa propre route (`getsettings`),
donc ce mappage GET ne sert aucun client.

**4. Paramètre de pagination non borné** —
`src/Api/Controllers/V1/MailMaintenanceController.cs:37,49` : `[FromQuery] int limit = 100`
passe directement en `.Take(limit)`. Un `limit` négatif atteint PostgreSQL en
`LIMIT -1` (erreur SQL ⇒ 500 au lieu de 400) ; un `limit` énorme matérialise toute
la table en une seule réponse JSON. Le repo sait faire : `PatientsController.cs:235`
applique `Math.Clamp(limit ?? 5, 1, 20)`.

**5. Trois rejets 403 hors contrat RFC 7807** —
`src/Api/Middleware/UserContextEnricherMiddleware.cs:462-467`, `:525-542`, `:548-562` :
ces chemins écrivent la réponse à la main — un `{"error":"…"}` en
`application/json` et deux chaînes brutes **sans `Content-Type`** (donc servies en
`text/plain`). Les trois frontends parsent `ProblemDetails` (règle 12) : ils
reçoivent un corps inexploitable et perdent le message actionnable (« votre compte
Keycloak n'a pas d'adresse MSSanté »). Le middleware étant en aval du gestionnaire
d'exceptions, il ne peut pas lever — mais `IProblemDetailsService` est injectable.

### Contenu attendu

1. **Purge** : réserver l'endpoint aux environnements de développement **et** à un
   rôle explicite, avec confirmation. En production, il doit être inatteignable
   (404/403). Arbitrage possible : le supprimer purement et simplement — à trancher
   dans la task, l'option la plus sûre étant préférée par défaut.
2. **Corps invalide ⇒ 400 problem+json** sur les douze actions, en réutilisant le
   patron `RequireBody` déjà en place plutôt qu'en inventant un mécanisme. Une
   solution transverse (filtre) est préférable à douze gardes recopiées, si elle ne
   casse pas le comportement voulu de `SuppressModelStateInvalidFilter`.
3. **Retirer le mappage GET** de l'action d'écriture des paramètres (405 attendu).
4. **Borner les paramètres de pagination** de l'endpoint de maintenance.
5. **Les trois rejets 403 en `application/problem+json`** via
   `IProblemDetailsService`, en préservant le message actionnable — et sans
   journaliser d'identifiant en clair (cohérence avec task-184, qui traite
   l'anonymisation de ces mêmes chemins).

### Hors scope

- Export/impression PDF → task-190.
- Le contenu des logs de ces chemins → task-184.
- Les deux `catch (Exception)` résiduels de `MailController` déjà suivis par
  task-066 (chemins de streaming post-premier-octet, corps générique — non
  ré-ouverts ici).

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test d'intégration : `DELETE /api/v1/maintenance/purge-mails` avec un jeton de
      praticien ordinaire est **refusé** hors développement (ce test doit échouer
      sur le code actuel — le vérifier explicitement)
- [ ] Test d'intégration : corps vide ou invalide sur **chacune** des 12 actions ⇒
      `400` `application/problem+json`, jamais `500` (dont le cas task-168 :
      `{"emailUid":""}` pour un type numérique)
- [ ] Test d'intégration : `GET /api/v1/settings/settings` ⇒ `405`, et les
      paramètres du praticien sont **inchangés**
- [ ] Test d'intégration : `list-emails?limit=-1` ⇒ `400` ; `limit` très grand ⇒
      borné, réponse de taille maîtrisée
- [ ] Test d'intégration : les trois rejets d'identité renvoient
      `application/problem+json` avec `title`/`detail`/`status` et conservent le
      message actionnable
- [ ] Non-régression : les corps valides continuent d'être traités à l'identique sur
      les 12 actions
- [ ] Aucune fuite de détail technique dans les corps d'erreur (pas de trace
      d'exception, pas de chaîne de connexion, pas de donnée de santé)

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. **Purge** : `curl -X DELETE http://localhost:{port}/api/v1/maintenance/purge-mails -H "Authorization: Bearer {jeton praticien}"`
   → refus (403/404) en configuration de type production. **Avant correctif :
   `200 {"success":true}` et la base mail est vidée** — ne tester le cas « avant »
   que sur une base jetable.
3. **Corps invalide** : `curl -X POST .../api/v1/ai/improve-text -H "Content-Type: application/json" -d ''`
   → `400` problem+json. Avant correctif : `500`.
   Répéter avec `PUT .../api/v1/patients/ins/{ins}/opposition -d 'null'` et
   `POST .../api/v1/diagnostics/recalculate-summary -d '{"emailUid":""}'`.
4. **GET qui écrit** : noter les paramètres actuels du praticien, puis
   `curl -X GET .../api/v1/settings/settings -d '{...}'` → `405`, paramètres
   inchangés. Avant correctif : les paramètres sont écrasés.
5. **Pagination** : `curl ".../api/v1/maintenance/list-emails?limit=-1"` → `400`
   (avant : `500`) ; `?limit=100000000` → réponse bornée.
6. **Rejet d'identité** : forger un jeton sans claim `mssEmail`, appeler n'importe
   quelle route → réponse `application/problem+json` lisible par les frontends
   (avant : `text/plain`).
7. Non-régression : parcours nominal complet (lecture, envoi, paramètres,
   recherche, IA) inchangé.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2
- **Exigences DSR honorées** : correctif de conformité — robustesse de l'API,
  intégrité des données (purge non gardée) et contrat d'erreur homogène (règle 12
  du projet, RFC 7807)
- **INS** : l'une des routes concernées porte l'INS en segment d'URL — le fond de ce
  sujet est traité par task-184, ne pas le dupliquer ici
- **Authentification PS** : inchangée (PSC / e-CPS). Le correctif ajoute un contrôle
  d'**habilitation** sur l'endpoint destructif, distinct de l'authentification
- **Habilitations** : **cœur du point 1** — un endpoint destructif doit exiger un
  rôle explicite, pas seulement une authentification valide
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : journaliser toute tentative d'appel de l'endpoint destructif
  (acceptée **ou** refusée) — évènement de sécurité à conserver
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : **à vérifier avec le humain** — l'endpoint de purge a-t-il
  été atteint en production ? Une perte de données de santé (art. 32 :
  disponibilité et intégrité) devrait être qualifiée. Les journaux d'accès à cette
  route sont la source à contrôler.
