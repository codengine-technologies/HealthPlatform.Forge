# todo-task-207.md — Le compteur d'événements de session IMAP est mort dans le chemin réellement exercé

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: task-204 (la section « Ressources & télémétrie » qui devait le publier)

> **Origine** : tir de contrôle télémétrie du 2026-07-29 (task-204). Le contenu
> attendu n°3 de task-204 demandait de publier « les événements de session IMAP »
> dans le rapport de tir. La ligne est **absente** — non par oubli du rapport, mais
> parce que le compteur n'a jamais aucune série.

## Objective

Rendre `mssante_imap_session_events_total` fidèle : il doit compter les créations,
logouts et expirations de session IMAP **quel que soit le chemin** qui les
provoque.

### La mesure

Pendant un tir où `mssante_imap_sessions_active` compte **215 sessions vivantes**
(et **1 001** à 200 praticiens, soit exactement 5 par praticien × 200) :

```
mssante_imap_session_events_total  ->  aucune série
```

Un compteur qui n'a aucune série n'est pas « à zéro » : il n'a **jamais** été
incrémenté depuis le démarrage du processus.

### La cause, lue dans le code

`MailClientSessionManager` a **deux** sites d'insertion dans `_sessions` :

| Ligne | Méthode | Instrumentée ? |
|---|---|---|
| 74-78 | `GetOrCreateImapClientAsync` | ✅ appelle `RecordImapSessionEvent("created")` |
| 277 | `GetOrCreateSession` | ❌ **rien** |

Or c'est `GetOrCreateSession` qu'emprunte le chemin du **verrou IMAP**
(`LockImapClientAsync` → `ImapLockScope`), et ce verrou est pris par les opérations
que le banc exerce. Le seul site instrumenté est donc celui que la charge
n'emprunte pas.

Les jauges `mssante_imap_sessions_active` / `_connected` / `_authenticated` ne
masquent pas le trou : elles observent `_sessions.Count`, donc elles voient bien
les sessions — ce qui rend l'absence du compteur d'autant plus trompeuse (« il y a
des sessions, donc l'instrumentation marche »).

## Contenu attendu

1. Instrumenter le second site d'insertion, ou mieux : **centraliser** la création
   de session de sorte qu'un futur troisième site ne puisse pas l'oublier (un seul
   point de passage vers `_sessions.GetOrAdd`).
2. Vérifier symétriquement les événements `logout` (ligne 423) et `expired`
   (ligne 523) : sont-ils sur des chemins réellement empruntés ?
3. Vérifier au banc que la ligne « Événements de session IMAP /s » apparaît enfin
   dans la section « Ressources & télémétrie » du rapport de tir.

## Hors scope

- Ajouter de nouveaux compteurs de session (le sujet est la fidélité de celui qui
  existe).
- Le reste de la télémétrie de task-204.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures)
- [ ] Test unitaire : une session créée **par le chemin du verrou IMAP**
      (`LockImapClientAsync`) incrémente le compteur — c'est le test qui aurait
      attrapé le défaut
- [ ] Test unitaire : une session réutilisée n'incrémente **pas** (pas de
      double comptage)
- [ ] Test unitaire : `logout` et `expired` sont comptés
- [ ] Test structurel : il n'existe qu'**un** point d'insertion dans `_sessions`
      (ou tous les points sont instrumentés) — un test qui échoue si un site non
      instrumenté réapparaît
- [ ] **Mesure au banc** : la ligne « Événements de session IMAP /s » est présente
      et non nulle dans le rapport, et son cumul est cohérent avec
      `mssante_imap_sessions_active` (≈ 5 par praticien)

## Manual Test Plan

1. Monter le banc (skill `loadtest-skill`), 200 praticiens re-câblés.
2. Tir court : `RPS=540 ... run.sh mixed --env VUS=60 --env DURATION=2m`.
3. Contrôle direct :
   ```bash
   curl -s --get 'http://127.0.0.1:9090/api/v1/query' \
     --data-urlencode 'query=sum by (event) (increase(mssante_imap_session_events_total[2m]))'
   ```
   Doit rendre au moins l'événement `created`, avec un cumul de l'ordre de
   1 000 (5 sessions × 200 praticiens).
4. `report.sh <json> --expected 100` : la table « Compteurs métier
   (`Mssante.MailProcessing`) » doit porter la ligne « Événements de session
   IMAP /s ».
