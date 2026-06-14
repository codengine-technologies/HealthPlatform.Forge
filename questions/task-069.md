# questions/task-069.md — Arbitrage sécurité requis avant implémentation

**Task** : `tasks/todo-task-069-tls-cert-validation-async-cache.md` (laissée en `todo-*`, non démarrée)
**Étape bloquée** : pré-/start — la task exige un arbitrage humain **avant** implémentation
**Date** : 2026-06-10 (run /forge)

## La question à trancher

En cas d'**indisponibilité du répondeur OCSP ou du point de distribution CRL**
(réseau coupé, répondeur lent > timeout, HTTP 5xx), quel comportement la chaîne
de validation des certificats IGC Santé doit-elle adopter ?

### Option A — Fail-open borné (disponibilité d'abord)
- Une réponse OCSP/CRL **en cache, même périmée**, reste acceptée pendant une
  fenêtre de grâce de **N heures** (à fixer : 4 h ? 24 h ?).
- Sans aucun cache disponible : la connexion est acceptée avec un évènement
  d'alerte journalisé (PGSSI-S) — statu quo actuel de fait : aujourd'hui un
  échec OCSP retourne `Result.Error` que les appelants traitent de manière
  hétérogène, et le timeout CRL de 30 s bloque la connexion sans la refuser.
- ✅ L'envoi/réception MSSanté reste disponible quand l'infrastructure ANS a un
  incident. ❌ Fenêtre pendant laquelle un certificat révoqué récemment pourrait
  être accepté.

### Option B — Fail-close (sécurité d'abord)
- Répondeur injoignable **et** pas de cache frais → connexion TLS refusée.
- ✅ Aucun certificat potentiellement révoqué accepté. ❌ Un incident du
  répondeur OCSP de l'IGC Santé rend la messagerie **indisponible** pour tous
  les praticiens (impact disponibilité HDS fort).

### Option C — Hybride (recommandation forge, à valider)
- Cache périmé toléré **4 h** (fenêtre de grâce courte), évènement Warning
  journalisé à chaque acceptation dégradée.
- Au-delà de 4 h sans réponse fraîche : fail-close.
- Timeout court (5 s) + 1 retry sur les téléchargements, conformément au DOD.

## Pourquoi la forge n'a pas tranché

La task elle-même le grave : « compromis PGSSI-S vs disponibilité de l'Espace
de Confiance MSSanté — décision sécurité à arbitrer ». C'est une décision de
posture de sécurité réglementaire, pas une décision d'implémentation.

## Pour débloquer

1. Choisir A, B ou C (et fixer N pour A/C).
2. Annoter la décision dans la section `## Comportement attendu` de la task
   (ou répondre ici).
3. Relancer `/start task-069` (ou `/forge` — la task est restée en `todo-*`).

## ✅ Résolution (humain, 2026-06-11)

**Option C retenue** — hybride, N = 4 h :
- Cache périmé toléré 4 h après expiration, Warning PGSSI-S journalisé à
  chaque acceptation dégradée.
- Au-delà de 4 h sans réponse fraîche, ou sans aucun cache : fail-close.
- La grâce ne s'applique qu'au statut « unknown » — un certificat révoqué
  est refusé immédiatement, sans fenêtre de grâce.
- Timeout 5 s + 1 retry sur les téléchargements OCSP/CRL.

Analyse complémentaire (session 2026-06-11) : le pattern `X509Chain`
`RevocationMode = Online` fail-closed (type bug #18021 côté client CPS) a été
évalué comme fallback — rejeté : il interroge les mêmes endpoints (aucun gain
de disponibilité), bloque le thread (jusqu'à 10 s/URL), et n'est pas testable
unitairement. Deux patterns en sont repris : discrimination `Revoked` (rejet
définitif) vs `RevocationStatusUnknown` (seul cas où la grâce s'applique), et
allowlist d'émetteurs en defense-in-depth, vérifiable de façon synchrone dans
le callback TLS.

Décision annotée dans la section `## Comportement attendu` de la task.
Question close — `/start task-069` relancé.
