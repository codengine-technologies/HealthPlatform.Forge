# task-422 — /develop : banc de charge injoignable (outillage)

**Étape** : `/develop`, avant le tir de la jambe B. **Nature** : outillage / infrastructure du banc, hors de portée de
la forge. Task laissée en `wip-*`.

## Constat (2026-11-05)

- **Banc mail du cluster (192.168.1.69) injoignable** : NodePorts 30993 (IMAP via Toxiproxy), 30994 (IMAP direct),
  30465 (SMTP), 30474 (API Toxiproxy) **fermés** ; ping sans réponse (100 % de perte) ; ports 22 et 6443 fermés aussi.
  L'API du banc, démarrée sur la branche, répond 503 `Impossible de joindre le serveur de messagerie. Erreur réseau:
  ConnectionRefused` sur `GET /mail/folders`.
- **Tireur k6bench (192.168.1.101) injoignable** : `remote.sh preflight` → `ssh: connect to host 192.168.1.101 port 22:
  Connection timed out`.
- Les deux machines du banc sont donc hors ligne ou coupées du poste (réseau du labo, alimentation, ou pfSense).
  `kubectl` n'est pas disponible depuis le poste : la forge ne peut ni diagnostiquer ni relancer le cluster.

## État laissé

- `api-mail`, branche `feat/task-422-mur-des-connexions-postgres-moins-de` : **une modification non commitée**,
  `src/AppHost/pgbouncer/pgbouncer.ini` `default_pool_size = 2 → 1` (le réglage de la jambe B). Rien n'est poussé
  au-delà de la branche vierge.
- AppHost du banc arrêté (API, DCP). Postgres local `postgres-pgvector` inchangé.

## Ce qu'il faut à l'humain

1. Rallumer / reconnecter le cluster du banc (192.168.1.69) et k6bench (192.168.1.101). Contrôle :
   `tests/loadtest-k6/remote/remote.sh preflight` vert (5052 et 9090 en 200), et
   `curl http://192.168.1.69:30474/proxies` qui liste les proxies Toxiproxy.
2. Si le pod Toxiproxy a redémarré, ses proxies sont perdus : rejouer le seed avec `--messages 0 --mail-host
   192.168.1.69` (skill `loadtest-skill`, « Mode DISTANT »).
3. Relancer `/develop task-422` : la forge reprend la jambe B (réglage déjà en place dans l'arbre de travail).

Aucune décision métier n'est en attente : seul le banc manque.
