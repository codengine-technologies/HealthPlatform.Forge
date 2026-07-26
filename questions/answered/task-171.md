# questions/task-171.md — Prérequis déploiement : domaine d'exposition d'api-mail

**Contexte** : ADR-2026-07-25 (backend pull du token PSC via cookie
`proxy_session_id`). Le cookie du psc-auth-proxy est posé avec `Domain=.weda.fr`
(hors dev). Le navigateur ne l'enverra donc qu'aux hôtes `*.weda.fr`.

**Constat (2026-07-25)** : les environnements clients pointent api-mail vers
`https://mss-api.xsd2code.com` :
- `Client/Angular/front/apps/weda2/src/environments/environment.prod.ts:16`
- `Client/Mobile/src/environments/environment.prod.ts:5`

alors que le proxy est sous `.weda.fr` (`auth-dev.office.weda.fr`,
`auth-proxy.dev.k8s.office.weda.fr`). **Sur cette topologie, le cookie ne
partira jamais vers api-mail** — le transport par cookie (phase 1 de l'ADR) ne
fonctionnera qu'en dev local (`localhost`, cookie host-only, ports ignorés).

**Questions pour l'humain** :

1. `mss-api.xsd2code.com` est-il un hébergement temporaire de dev/démo, avec une
   bascule prévue vers un hôte `*.weda.fr` (ex. `mss-api.weda.fr` ou
   `mss-api.dev.k8s.office.weda.fr`) ? Si oui, à quelle échéance et sur quels
   environnements ?
2. Sinon, faut-il activer le **plan B de l'ADR** (transport du session id par
   header explicite — nécessite d'exposer le session id au client : déjà le cas
   sur mobile via la réponse CIBA `ProxySessionId`, à créer côté web) ? Cela
   affaiblit la protection HttpOnly et mérite un arbitrage sécurité.
3. Liste des origines front à whitelister dans `Cors:AllowedOrigins` d'api-mail
   par environnement (obligatoire dès que `.AllowCredentials()` est actif —
   aucune wildcard possible).

**Impact** : ne bloque PAS l'implémentation ni les tests locaux de task-171
(fallback `X-PSC-Token` conservé par ailleurs). Bloque la mise en service du
chemin cookie hors dev, et donc le démarrage de task-172 sur les environnements
concernés.

---

## ✅ Réponse humaine (2026-07-25)

Décision : **on attend la bascule d'api-mail sous `*.weda.fr`** (question 1 —
pas de plan B header, le transport cookie est conservé). Les tasks 171 et 172
sont mises **on hold** (`tasks/onhold/`) et seront réactivées à ce moment-là.
La question 3 (whitelist `Cors:AllowedOrigins` par environnement) sera à
trancher à la réactivation.
