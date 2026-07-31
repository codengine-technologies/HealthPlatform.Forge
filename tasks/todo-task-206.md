# todo-task-206.md — Le banc lève une exception par requête, et ce bruit noie la télémétrie

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-204 (la colonne « Exceptions /s » qui a rendu le défaut visible)
**Priorité**: **4/6** — Fidelite du banc (ordre arrêté le 2026-07-31, objectif montée en charge)
> Une exception par requete (~1 400/s au plafond) : le banc n'exerce pas le chemin d'authentification de production. Un chiffre de capacite mesure sur un autre chemin que celui deploye n'est pas opposable.

> **Origine** : tir de contrôle télémétrie du 2026-07-29 (task-204). La colonne
> « Exceptions /s » que task-204 vient d'ajouter au rapport a immédiatement montré
> un débit d'exceptions absurde. Personne ne l'avait vu avant, faute de la mesurer.

## Objective

Faire en sorte qu'un tir de charge n'exerce pas un chemin de code qui **lève une
exception à chaque requête**, pour deux raisons également importantes : la mesure
n'est pas fidèle au chemin de production, et le bruit rend la colonne
« Exceptions /s » inutilisable pour détecter une vraie anomalie.

### La mesure

| Charge | `SecurityTokenMalformedException` | Débit d'exceptions |
|---|---|---|
| 106 req/s (20 praticiens) | 12 668 en 121 s | ~105/s, **≈1,2 par requête** |
| ~480 req/s (200 praticiens) | — | ~110-145/s **par réplica** |
| ~858 req/s (200 praticiens) | — | ~233-290/s **par réplica**, soit **>1 200/s** au total |

Le débit croît linéairement avec la charge : c'est **une exception par requête**,
pas un incident.

Autres familles relevées, pour mémoire (elles ne sont pas l'objet de cette task) :
`FolderNotFoundException` (l'absence de dossier `Sent` sur les boîtes du banc,
connue et documentée comme bénigne), `HttpRequestException`, `FlagsmithAPIError`,
`IOException`, `XmlException`.

### La cause

Le banc envoie `X-PSC-Token: loadtest` — une valeur non vide mais **pas un JWT** —
parce que le profil `https-load-test` pose `MSS_ENFORCE_PSC_IDENTITY=false` et que
« n'importe quelle valeur non vide suffit ». Or le code **tente quand même de
parser le token** avant de constater qu'il n'a pas à l'exiger : le parse lève,
l'exception est avalée, et la requête continue normalement.

⚠️ **En production le token est valide, donc ce chemin ne lève pas.** Ce n'est
donc pas un défaut de production — c'est un défaut de **fidélité du banc** (la
mesure inclut un coût que la production ne paie pas) doublé d'un défaut
d'**observabilité** (le bruit masque les vraies exceptions). Les deux se corrigent
ensemble.

### Deux voies, à trancher dans l'US

1. **Ne pas parser quand l'enforcement est désactivé** — le garde `enforce=false`
   doit court-circuiter *avant* la tentative de parse, pas après. Corrige la cause
   pour tout appelant, banc ou non. À préférer si le parse n'a aucun autre effet
   utile dans ce mode.
2. **Faire forger au banc un token syntaxiquement valide** (seed / harnais k6) —
   la mesure exerce alors exactement le chemin de production, y compris son coût
   de parsing. Plus fidèle, mais laisse le parse spéculatif en place.

Les deux sont compatibles ; la voie 1 est la correction, la voie 2 la fidélité.

## Contenu attendu

1. Localiser le site du parse spéculatif et **nommer** pourquoi il s'exécute alors
   que l'enforcement est désactivé.
2. Mettre en œuvre la voie retenue (argumenter le choix dans la task).
3. Vérifier au banc que le débit d'exceptions s'effondre, et que les familles
   restantes sont **toutes** explicables.
4. Documenter dans le skill `loadtest-skill` la lecture attendue de la colonne
   « Exceptions /s » (quel ordre de grandeur est normal après correction).

## Hors scope

- `FolderNotFoundException` / l'absence de dossier `Sent` sur les boîtes du banc :
  déjà documentée comme bénigne, à traiter seulement si le banc provisionne un
  `Sent` un jour.
- La famine de ThreadPool et le plafond de capacité (task-205).

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Test unitaire : avec l'enforcement **désactivé** et un token non-JWT,
      **aucune exception n'est levée** sur le chemin de la requête
- [ ] Test unitaire : avec l'enforcement **activé**, un token invalide est toujours
      rejeté (la correction ne desserre aucun contrôle)
- [ ] **Mesure au banc** : à ~480 req/s, `SecurityTokenMalformedException`
      **= 0** sur la fenêtre du tir (contre ~110-145/s par réplica)
- [ ] Après correction, chaque famille d'exception restante est nommée et
      expliquée dans le rapport de tir
- [ ] `loadtest-skill` : la lecture attendue de « Exceptions /s » est écrite

## Manual Test Plan

1. Monter le banc (skill `loadtest-skill`), 200 praticiens re-câblés
   (`--users 200 --messages 0`).
2. Tir court : `RPS=540 ... run.sh mixed --env VUS=60 --env DURATION=2m`.
3. Relever le débit d'exceptions par type :
   ```bash
   curl -s --get 'http://127.0.0.1:9090/api/v1/query' \
     --data-urlencode 'query=sum by (error_type) (increase(dotnet_exceptions_total[2m]))'
   ```
   `SecurityTokenMalformedException` doit être **absent**.
4. Lire la colonne « Exceptions /s » de la table « Par réplica api-mail » du
   rapport : elle doit tomber à un ordre de grandeur exploitable.
5. Contrôle de non-régression fonctionnelle : les tirs `folders` / `read` /
   `search` / `send` répondent toujours 200 (aucun 401/403 nouveau).
