# todo-task-270.md — La recherche de dossier ne repaie plus 5 allers-retours IMAP à chaque cache-miss

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015

## Objectif

L'appel `folder` (`GET /mail/folders/{name}`) est le **premier poste du
dashboard** — 63 % de son temps serveur (3 899,7 s au palier 500 de la campagne
du 2026-08-23), et le dashboard est lui-même le deuxième poste global (23,1 %).
Vert au SLO, mais gros consommateur : le point aveugle que task-262 a
instrumenté précisément pour rendre cette US possible.

**Le seuil de reprise fixé par task-262 est franchi, et chiffré.** Le compteur
de sollicitations (première campagne où il couvre ce chemin) donne, sur la
fenêtre du tir (`mssante_mail_server_solicitations_total`, Prometheus) :

| Opération | Commandes IMAP | Occurrences |
|---|---|---|
| `GetFolderQuery` (recherche complète) | `resolve_folder` + `open_folder` + `status_folder` + `search_folder` + `close_folder` = **5 allers-retours** | 16 283 exécutions |
| `GetFolderStatus` (chemin `today`) | `resolve_folder` + `status_folder` = 2 allers-retours | 52 749 exécutions |

La route `folder` a été appelée ~43 200 fois (dashboard + inbox) : **~38 % des
appels partent en recherche complète à 5 allers-retours** (~500 ms sous 100 ms
de latence MSSanté), les autres sont servis par le cache. C'est exactement la
bimodalité de la route : p50 127 ms / p95 698 ms — et ce p95 est **plat de 100
à 500 médecins** (696 → 699 → 698) : un coût fixe par appel, pas un effet de
charge. Le remède est donc côté **contenu de l'appel**, pas côté capacité.

**Contenu attendu** (les deux remèdes nommés par task-262, à arbitrer sur
mesure par `/develop`) :

1. **Réduire le coût d'un cache-miss** : la séquence à 5 allers-retours
   contient un `STATUS` **et** un `SEARCH` sur un dossier qu'elle vient
   d'ouvrir — examiner ce que le `SEARCH` apporte que le `STATUS` (ou l'état
   du dossier ouvert) ne donne pas déjà, et supprimer les commandes redondantes.
   Toute réduction se **prouve par le compteur de sollicitations** (c'est
   l'instrument posé pour ça), jamais par la seule latence.
2. **Réduire la part de cache-miss** : la durée de fraîcheur du cache de
   dossier est un **arbitrage produit à énoncer** — un compteur de dossier
   plus frais coûte des allers-retours, un compteur périmé ment au médecin.
   La fraîcheur choisie doit être écrite (dans le code et la task), pas
   implicite.

**Gain attendu** : passer un cache-miss de 5 à 2-3 allers-retours ≈ −200 à
−300 ms sur ~16 000 appels/campagne ≈ **−3 000 à −4 900 s de temps serveur**
(le dashboard passerait sous ~15 % du temps serveur) ; p95 du dashboard
~700 → ~400-500 ms.

**Ce qui n'est PAS dans le périmètre** : la page d'en-têtes
(`GET …/emails/{ids}`, task-194/261) ; le chemin `today` à 2 allers-retours
(déjà minimal) ; toute modification du contrat de la route.

## Definition of Done

- [ ] Build passes (0 errors), tests pass (0 failures) sur api-mail
- [ ] Le nombre d'allers-retours IMAP d'un cache-miss de `GetFolderQuery` est
      **réduit et prouvé par le compteur de sollicitations** (test
      d'intégration : compte exact des commandes enregistrées avant/après,
      dans l'ordre — même style que les tests de task-262)
- [ ] Ce que le médecin voit est inchangé : mêmes compteurs de dossier, même
      liste — >= 1 test d'intégration sur le vrai dépôt comparant la réponse
      avant/après
- [ ] Si la durée de fraîcheur du cache change : la valeur et sa justification
      sont écrites en commentaire au point de décision, et un test fixe le
      comportement (un dossier modifié côté IMAP est vu au plus tard après
      {fraîcheur})
- [ ] Aucune régression sur le chemin `GetFolderStatus` (`today`) — ses 2
      allers-retours restent 2, prouvé par le même compteur
- [ ] Unit tests pour toute nouvelle branche (>= 1 par branche)
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Lancer le banc local : `cd Api/Mail && dotnet run --project src/AppHost --launch-profile https-load-test`
- Seeder : `dotnet run --project tests/mss.mail.loadtest.seed -- --users 5 --messages 10 --api http://127.0.0.1:5052`
- Appeler `GET /api/v1/mail/folders/INBOX` deux fois (identité loadtest-1,
  session stable) : relever dans Prometheus
  `mssante_mail_server_solicitations_total{operation="GetFolderQuery"}` —
  le premier appel enregistre la séquence réduite, le second est un cache-hit
  (aucune commande)
- Vérifier que la réponse JSON (compteurs, uids) est identique à celle
  d'avant le correctif sur le même seed
- **Au banc (clôture de l'US, non bloquant pour le merge)** : tir journey
  distant iso-conditions 2026-08-23 — `dashboard,call:folder` p95 < 500 ms au
  palier 500 et part du dashboard < 18 % du temps serveur

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — optimisation de performance interne
- **Exigences DSR honorées** : non applicable — comportement fonctionnel inchangé
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — IMAP interne au périmètre MSSanté existant
- **Tracé PGSSI-S** : inchangé — la consultation de dossier reste journalisée à l'identique
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — inchangé
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : `feat/task-270-folder-imap-roundtrips` — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-270-folder-imap-roundtrips
- `dtos-mss` (pushed, auto-inclus) : `feat/task-270-folder-imap-roundtrips` — https://github.com/codengine-technologies/HealthPlatform.Dtos.Mss/tree/feat/task-270-folder-imap-roundtrips (aucun changement de contrat attendu — la task exclut toute modification du contrat de la route)
