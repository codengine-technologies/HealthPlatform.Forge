# todo-task-050-keycloak-protocol-mappers-msssub-mssrpps.md — Protocol Mappers Keycloak pour `mssSub` & `mssRpps`

**Repos**: devops *(hors automation forge — pilotage manuel)*
**Dependencies**: task-049 (alimentation des attributs user), précède l'enforcement de task-048
**Epic**: E009

> ⚠ **Repo `devops` hors automation forge.** Cette task documente la
> configuration Keycloak à appliquer manuellement (ou via le pipeline
> IaC du realm s'il existe).

## Objectif

Configurer Keycloak pour projeter les deux nouveaux attributs
utilisateur écrits par task-049 (`mssSub` et `mssRpps`) en claims du
JWT émis pour les clients d'`api-mail`, afin que
`UserContextEnricherMiddleware` (task-048) puisse les lire via
`context.User.FindFirstValue("mssSub" | "mssRpps")`.

## Configuration à appliquer

### Realm cible

Le realm Keycloak qui sert les tokens consommés par `api-mail`
(typiquement le même que celui qui porte le claim `mssEmail`
actuel).

### Mappers à créer

Deux Protocol Mappers de type `User Attribute`, identiques en
mécanisme à celui qui projette déjà `mssEmail`.

| # | Champ | Mapper 1 (`mssSub`) | Mapper 2 (`mssRpps`) |
|---|---|---|---|
| 1 | Name | `mssSub` | `mssRpps` |
| 2 | Mapper Type | `User Attribute` | `User Attribute` |
| 3 | User Attribute | `mssSub` | `mssRpps` |
| 4 | Token Claim Name | `mssSub` | `mssRpps` |
| 5 | Claim JSON Type | `String` | `String` |
| 6 | Add to ID token | `false` (sauf si déjà la convention pour `mssEmail`) | idem |
| 7 | Add to access token | **`true`** | **`true`** |
| 8 | Add to userinfo | `true` (recommandé pour debug) | `true` |
| 9 | Multivalued | `false` | `false` |
| 10 | Aggregate attribute values | `false` | `false` |

### Où attacher les mappers

Conformément à la convention en place pour `mssEmail` :
- Soit sur le **Client Scope** dédié aux services MSSanté (recommandé,
  réutilisable)
- Soit directement sur le **Client** `api-mail` (si pas de scope partagé)

À aligner avec la pratique existante du repo `devops`.

### Vérification post-configuration

1. Sur un user de test qui a `mssSub` et `mssRpps` provisionnés dans
   Keycloak Admin :
   - Obtenir un access token via le flow OIDC standard.
   - Décoder la partie payload (jwt.io ou équivalent).
   - Vérifier la **présence** de `"mssSub": "<uuid>"` et
     `"mssRpps": "<12 chiffres>"` dans le payload.
2. Sur un user sans ces attributs (legacy, non encore opt-in) :
   - Le payload ne doit **pas** contenir ces clés (mappers absents ne
     génèrent pas de clé vide).
   - `api-mail` traitera comme `incomplete` (cf. task-048 EventId 3722).

## Definition of Done

- [ ] Mapper `mssSub` créé, audité sur un token réel
- [ ] Mapper `mssRpps` créé, audité sur un token réel
- [ ] Présence vérifiée sur access token (pas seulement ID token)
- [ ] Documentation de la modification ajoutée au repo `devops`
      (export realm JSON commit, ou Terraform/script, selon la
      convention IaC existante)
- [ ] Modification appliquée sur tous les environnements pertinents
      (Dev → Staging → Prod), dans cet ordre

## Runbook — bascule d'enforcement task-048

Une fois task-049 + task-050 déployées en prod et au moins 24 h
d'observation passées :

1. Vérifier dans Seq la **proportion** d'`EventId 3722` (KC incomplete)
   parmi les requêtes online. Cible : < 5 % du trafic (les retardataires
   seront forcés à un nouveau login PSC pour acquérir les claims).
2. Vérifier dans Seq la **proportion** d'`EventId 3723` (mismatch).
   Cible : aussi bas que possible. Tout pic ici = leak silencieux
   actuel qu'on est sur le point de couper.
3. Préparer la bascule : passer `MSS_ENFORCE_PSC_IDENTITY=true` sur
   `api-mail` en prod (rolling restart).
4. Surveiller le taux de 403 sur les endpoints `/api/v1/mail/*`
   immédiatement après bascule. Pic attendu et borné par le taux
   d'EventId 3722+3723 observé en phase 1.
5. Communication utilisateur : si pic > 5 %, message UI dédié
   « Reconnexion requise après changement de carte CPS » + redirect
   logout.

## Manual Test Plan

1. Sur Dev, après application des deux mappers : se connecter via PSC.
2. Récupérer le `access_token` en cours (DevTools → Network ou Seq).
3. Décoder le payload sur jwt.io.
4. Confirmer la présence de `mssSub`, `mssRpps`, `mssEmail` côte à
   côte.
5. Refaire le test sans avoir provisionné l'attribut côté user
   (compte legacy) → claims absents (et non vides).
