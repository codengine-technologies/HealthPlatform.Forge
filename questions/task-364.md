# questions/task-364.md — /e2e rouge sur E2E-AI-001 : serveur de messagerie e2e instable en fin de suite

**Étape** : `/e2e task-364`, relancée le 2026-10-10 (nuit).
**Nature du blocage** : **rouge hors quarantaine** (règle 3, sans exemption), dont la cause relevée
est l'**environnement e2e**, et non le code de la task. Parité verte.

## Ce qui est réglé

Trois défauts des tests Angular (`e2e/mss-e2e/specs/functional.e2e.ts`, corrigés, **à commiter
par l'humain** sur TFS) :
1. E2E-DETAIL-004 : l'étiquette `Lecture e2e` était refusée par le serveur (400, « Tag name must not
   contain spaces ») → `Lecture-e2e`.
2. E2E-WEDA-002 : `check()` sur `ds-radio-button` / `ds-checkbox`. Sans zone.js, `aria-checked`
   change au tick suivant, après la vérification de Playwright → `click()` + `expect(…).toBeChecked()`.
3. E2E-DETAIL-004 : le message suivant était ouvert alors que le filtre « Bio à acquitter » était
   encore actif → le filtre est retiré par sa puce, sans quitter la page.

Au dernier run, **E2E-DETAIL-004, E2E-WEDA-002 et E2E-LIVE-001 sont verts**. Mobile : 31/31.

## Ce qui reste rouge : E2E-AI-001 (angular), aux deux essais

- **Erreur** : `openInbox` → `le dossier INBOX est ouvert` : `.mail-list-title` absent.
- **Instantané** : dossiers listés, quota « non disponible », liste « Aucun message ».
- **Signature récurrente** : à chaque run, un test différent de `live-ai.e2e.ts`, joué en fin de
  suite, tombe sur un serveur de messagerie e2e qui ne répond plus.

  | Run | Test en échec | Symptôme |
  |---|---|---|
  | 1 | COMPOSE-002 | 503 sur `/mail/folders` et `/account/quota` |
  | 2 | LIVE-001 | « An established connection was aborted » à la livraison |
  | 3 | AI-001 | quota indisponible, liste vide |

  Aucun lien relevé avec l'interface modifiée par la task.

## Diagnostic (Seq, 2026-10-10 21:23 UTC)

- **Erreur exacte** (api-mail, `ImapService`) : `IO error connecting to IMAP server` →
  `System.IO.IOException: An established connection was aborted by the software in your host machine`
  (`SocketException 10053`), levée dans `SslStream` au moment où api-mail ouvre une **nouvelle**
  connexion IMAP (`🌱 New ImapClient`). En 50 ms, le dossier rouvert, INBOX et le quota échouent
  tous de la même façon. Ces réponses en 500/503 ne sont que la conséquence.
- **Corrélation forte** : les connexions IMAP neuves ouvertes depuis le début de la voie
  atteignent **~100** au moment exact de chaque échec. Le run 2 en compte 107 entre 21:13 et
  21:17, puis échoue à 21:17. Le run 3 en compte ~100 entre 21:19 et 21:23, puis échoue à 21:23.
  La voie mobile (91) passe. Or le banc fixe `mail_max_userip_connections = 100`
  (`src/AppHost/dovecot/dovecot.conf`), avec un seul praticien et une seule IP.
- **Mécanisme probable** : chaque test ouvre une nouvelle session navigateur, donc un nouveau
  `Client-Session-Id`. api-mail y attache sa propre connexion IMAP, gardée **5 min**
  (`ImapIdleTimeout`), parfois sur plusieurs réplicas et avec une voie d'écriture à part. La voie
  Angular, ~35 tests en ~5 min, empile les connexions jusqu'au plafond : les dernières sont
  refusées. Le fichier `live-ai.e2e.ts`, joué en dernier, prend toujours.
- **À confirmer** : par les journaux Dovecot (`doveadm who`, ou « Maximum number of connections
  from user+IP exceeded ») d'un run gardé debout. Le conteneur est retiré au démontage.

## Décision prise (humaine, 2026-10-11)

- Plafond du banc relevé : `mail_max_userip_connections = 1000` (api-mail `ca7e9e0a`, branche
  `feat/task-364-lecture-panneau-actions`).
- L'empilement en production (iframe Weda) est confié à **task-365** (analyse puis correctif).
- Suite : relancer `/e2e task-364`.

À faire à la relance, de toute façon : la **preuve par mutation d'E2E-DETAIL-004** (toujours due).

## État

- Démontage complet : ports libres, aucun conteneur e2e résiduel.
- `## E2E log` du task file à jour (rouge). La task reste en `wip-task-364.md`. Chaîne arrêtée avant `/review`.
- Aucune donnée de santé ici : identités synthétiques du banc e2e.
