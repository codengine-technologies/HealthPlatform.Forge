# todo-task-382.md — La session de weda2 se ferme vraiment quand le médecin s'absente, et la connexion PSC aboutit

**Repos**: client-angular, api-mail (catalogue e2e `Api/Mail/e2e/scenarios.yml` seulement)
**Dependencies**: task-370 (même module d'authentification ; `refreshAndReplay`, `isSessionLossError`, `injectSessionRefreshDeps`)
**Epic**: E016
**Single frontend**: true
**Priorité**: **1** — sur un poste de cabinet partagé, la session d'un médecin absent ne se ferme jamais ; la connexion PSC peut boucler ou rester bloquée.

> **Origine.** Scindée de task-370 le 2026-10-14 (décision humaine : task-370 réduite à ANG-06). Audit de détection
> de bugs du client Angular du 2026-10-13 (**ANG-07 ✔, ANG-23, ANG-24, ANG-66, ANG-67, ANG-69, ANG-71**).
> Le code de ces constats a été écrit et prouvé au premier passage de task-370 (travail annulé `915a9339`, develop
> log dans le control plane `d86d9b8:tasks/done-task-370.md`) : réutilisable, test d'abord.

## Ce qui est établi

- **ANG-07** — `auto-logout.service.ts:207-240` : `initialize()` n'est appelé nulle part ; à l'échéance, `triggerLogout()` journalise « Auth store not initialized » et ne déconnecte pas. Le bouton « Se déconnecter » du dialogue ne fait rien. Un réveil de veille au-delà de la fenêtre n'ouvre aucun dialogue.
- **ANG-23** — « Se connecter avec Pro Santé Connect » (écran « PSC requis ») navigue vers `/login`, une route qui n'existe pas ; `loginPsc()` n'est jamais appelé.
- **ANG-24 / ANG-66** — Aucun garde-fou contre une boucle callback ↔ proxy ; un retour d'erreur OAuth (annulation PSC) laisse un spinner infini.
- **ANG-67 / ANG-69 / ANG-71** — Créneau de rafraîchissement partagé libéré au désabonnement d'un appelant ; rechargement inutile au callback qui perd la page demandée ; repli sur `preferred_username` jamais appliqué (`??` après `join`).
- Déjà dans l'arbre client-angular (non commité, task-370) : `loginPsc()` pose un `state` CSRF stocké, avec son test.

## Objective

Que le médecin qui s'absente soit **toujours** déconnecté à l'échéance prévue (mode autonome ; le mode embarqué reste
régi par Weda), et que la connexion Pro Santé Connect aboutisse ou affiche une erreur actionnable.

### Périmètre

1. **Déconnexion pour inactivité réelle** : le service reçoit le store ; `timeRemaining <= 0` (réveil de veille) déconnecte sans dialogue ; le bouton du dialogue déconnecte. Le mode embarqué reste régi par Weda (inchangé).
2. **« Se connecter avec Pro Santé Connect »** branché sur `loginPsc()`, avec `state` CSRF.
3. **Callback** : relances bornées puis écran d'erreur avec « Réessayer » ; `error` / `error_description` affichés ; pas de rechargement superflu ; plus de `login()` dans `$exchangeCodeForToken`.
4. Corrections mineures : `finalize` du créneau partagé avant `shareReplay` ; `||` pour le repli `preferred_username`.

## Definition of Done

- [ ] Build et tests weda2 verts
- [ ] Tests unitaires rouges d'abord :
  - [ ] à l'échéance d'inactivité, `logout()` du store est appelé ; au réveil après l'échéance, aussi ; le bouton du dialogue aussi
  - [ ] « Se connecter avec Pro Santé Connect » appelle `loginPsc()` avec un `state` stocké
  - [ ] au-delà de N relances du callback, l'écran d'erreur s'affiche ; un `?error=` affiche son message
  - [ ] l'annulation d'un abonné ne libère pas le créneau de rafraîchissement en vol
- [ ] Scénario E2E-AUTH-003 « Être déconnecté après une période d'inactivité » ajouté au catalogue (angular `requis` ; mobile `non-applicable` — l'application mobile n'a pas de déconnexion pour inactivité, constaté au `/start` de task-370)
- [ ] Aucun jeton, `sub` ni adresse ajouté aux journaux

## Manual Test Plan

1. Rester inactif jusqu'au dialogue, ne rien faire → déconnexion et écran de connexion. Recommencer en cliquant « Se déconnecter ».
2. Mettre le poste en veille au-delà de la durée d'inactivité, le réveiller → déconnexion immédiate.
3. Compte sans boîte ni jeton PSC : écran « PSC requis », bouton « Se connecter avec Pro Santé Connect » → redirection PSC.
4. Annuler la connexion PSC → message d'erreur avec « Réessayer », pas de spinner infini.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif de la session de la plateforme
- **Exigences DSR honorées** : non applicable — rétablit le socle PGSSI-S (verrouillage de session après inactivité)
- **INS** : non applicable
- **Authentification PS** : PSC / e-CPS (niveau eIDAS substantiel) inchangés ; la déconnexion pour inactivité du poste partagé redevient effective
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : déconnexion pour inactivité et perte de session journalisées côté client (cause seulement, sans jeton ni `sub`)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — protège l'accès aux DSCP sur un poste partagé
- **AIPD / impact RGPD** : inchangé

