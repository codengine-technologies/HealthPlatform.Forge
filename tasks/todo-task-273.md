# todo-task-273.md — L'arrivée sur le tableau de bord ne coûte plus un quart du temps serveur

**Repos**: api-mail
**Dependencies**: —
**Epic**: E015

## Objectif

L'arrivée sur le tableau de bord est **verte au SLO** (p50 11 ms, p95 476 ms
pour 300/1 500) et c'est précisément pour ça que personne ne la regarde :
c'est pourtant le **deuxième poste du temps serveur du palier 1000** —
**24,8 %** (14 615 s), juste derrière l'envoi
(`Api/Mail/tests/loadtest-k6/reports/2026-08-25/report-journey-1000-solo-postimap-20260825-151054.md`,
section « Axes d'amélioration » : « vert au SLO mais gros consommateur —
invisible d'un rapport qui ne lit que les percentiles »).

La ventilation multi-appels attribue le coût : sur les quatre appels du
geste, **`GET /mail/folders/{folder}` porte 59 % du temps de l'étape**
(8 630 s, p50 133 ms, p95 596 ms, n=40 655), devant `today` (3 393 s, p50
6 ms mais p95 469 ms — dispersion énorme), `folders` (2 324 s) et `coverage`
(267 s, négligeable). Dispersion p95/p50 de l'étape : **×45** — un coût qui
dépend de la charge ou de la donnée, pas un coût fixe.

C'est le geste **le plus fréquent du parcours** (162 620 appels sur le tir,
4 requêtes à chaque passage) : chaque milliseconde gagnée ici est multipliée
par un volume qu'aucune autre étape n'approche.

**⚠️ La cause n'est PAS encore établie — l'établir fait partie de l'US,
avant tout remède.** Cette EPIC a déjà payé une US écrite sur une cause
supposée (task-222, annulée). Faits mesurés disponibles pour démarrer :
`GetFolderQuery` attend 0,45 s (p95) sur le verrou `imap_session` et le
détient 1,7 s ; `GetFolderStatus` le détient 3,2 s ; à l'inverse la mémoire
du banc (2026-08-08) mesurait « l'ouverture du dossier est gratuite (7 ms) »
sur le chemin inbox — les deux lectures doivent être réconciliées par la
télémétrie (décomposition d'une requête représentative par `TraceId`,
task-243/256 pour la part base, verrous task-211 pour la part session).

**Pistes de remède à arbitrer une fois la cause établie** (aucune n'est
acquise) : mémoïsation courte des compteurs de dossier par praticien
(le dashboard relit des compteurs que `today`/`folder` viennent de calculer),
regroupement côté serveur des quatre appels en un, réduction du travail
IMAP sous le verrou de session. Un remède qui change le contrat des routes
impliquerait les frontends — **ce découpage-là repasserait par le PO**
(cette US est volontairement scopée backend, contrat d'API inchangé).

**Gain attendu** : l'appel `folder` pèse 8 630 s serveur sur le tir — une
division par deux du geste dashboard rend ~12 % du temps serveur total de la
plateforme, sans changer une ligne de front.

**Hors périmètre** : la page d'en-têtes de l'inbox (`GetMailsByUids`,
matérialisation dominée par les objets de fil — finding distinct, US à part
si le PO le décide) ; tout changement de contrat d'API ou de front.

## Definition of Done

- [ ] Build passes (0 errors), tests pass (0 failures) sur api-mail
- [ ] La cause du coût de `GET /mail/folders/{folder}` au volume du dashboard
      est **établie et écrite dans la task** (décomposition par phase :
      verrou / IMAP / base / matérialisation), AVANT le choix du remède
- [ ] Le remède retenu est appliqué **sans changement de contrat d'API**
      (mêmes routes, mêmes DTO) — les frontends ne sont pas touchés
- [ ] Un test d'intégration fige le comportement optimisé (ex. : deux
      arrivées dashboard successives du même praticien → la seconde ne
      repaie pas le travail identifié comme dominant ; adapter l'assertion
      à la cause établie)
- [ ] Si une mise en cache est retenue : sa péremption est bornée et testée
      (un nouveau message reçu est visible dans les compteurs au plus tard
      à l'expiration — la valeur du TTL est un choix PO à faire valider,
      proposer ≤ 30 s), et l'invalidation sur action du praticien
      (lecture, envoi, suppression) est testée
- [ ] `DbOperationScope`/verrous (task-211/243) continuent de mesurer le
      chemin optimisé — la prochaine campagne peut chiffrer le gain
- [ ] Unit tests pour tout nouveau service/handler (>= 1 par méthode publique)
- [ ] Aucune donnée de santé en clair dans les logs

## Manual Test Plan

- Lancer le banc local : `cd Api/Mail && dotnet run --project src/AppHost --launch-profile https-load-test`
- Seeder : `dotnet run --project tests/mss.mail.loadtest.seed -- --users 5 --messages 20 --api http://127.0.0.1:5052`
- Rejouer deux fois de suite le quatuor du dashboard pour la même identité
  (`GET /mail/folders`, `GET /mail/folders/INBOX`, `GET .../emails/today`,
  `GET /sync/coverage`, en-têtes loadtest-1, `Client-Session-Id` stable) :
  la seconde passe est sensiblement plus rapide sur l'appel identifié comme
  dominant
- Envoyer un message vers loadtest-1 (seed ou `sendmail`), rejouer le
  quatuor : les compteurs reflètent le nouveau message (pas de cache menteur)
- **Au banc (clôture de l'US, non bloquant pour le merge)** : tir journey
  distant iso-conditions avec `report-journey-1000-solo-postimap-20260825` —
  part du dashboard dans le temps serveur < 15 % (aujourd'hui 24,8 %),
  étape 1 toujours verte au SLO

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — optimisation de performance interne, aucun
  changement fonctionnel ni de contrat d'API
- **Exigences DSR honorées** : non applicable — comportement fonctionnel inchangé
- **INS** : non applicable — aucun traitement patient modifié
- **Authentification PS** : inchangée (PSC en amont)
- **Habilitations** : inchangées — un cache éventuel est strictement par
  praticien (clé = identité PS), jamais partagé entre praticiens
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé — aucun accès nouveau, mêmes évènements
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — inchangé
- **AIPD / impact RGPD** : un cache par praticien de compteurs de dossiers ne
  crée pas de nouveau traitement ; contenu limité à des dénombrements, TTL
  court, pas de contenu de message — impact nul
