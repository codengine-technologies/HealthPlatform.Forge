# todo-task-378.md — À l'entrée et dans la gestion des messageries, une panne est dite comme une panne, et chaque action dit si elle a réussi

**Repos**: client-angular, api-mail
**Dependencies**: task-374 (cycle de vie de la session de boîte)
**Epic**: E016
**Single frontend**: true
**Priorité**: **2** — une panne passagère envoie un médecin qui a sa carte vers « reconnectez-vous avec PSC », ou vers un rattachement voué à l'échec ; une boîte en échec d'authentification reste bloquée sans issue indiquée.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-28, ANG-29, ANG-76**).

## Ce qui est établi

- **ANG-28** — `mailbox-session.store.ts:410-438` : tout échec du chargement des boîtes vaut « zéro boîte » ; injoignable → écran « PSC requis » ; liste en échec mais statut en ligne → onboarding (en embarqué, rattachement d'une boîte déjà rattachée, 409). Cas Probable : après détachement, 409 `SESSION_MAILBOX_MISMATCH` sur `initialize()` sans `Client-Session-Id`.
- **ANG-29** — « Ré-essayer l'authentification » (`mss-mailbox-management.component.ts:244-246`) ne fait rien : une boîte `AuthFailing` n'est pas sélectionnable et ne repasse `Active` que sur un login XOAUTH2 réussi.
- **ANG-76** — détacher, rattacher à nouveau, définir par défaut ignorent l'échec (un détachement échoué de la dernière boîte déconnecte) ; « déjà rattachée » et « session PSC requise » s'affichent « identifiants refusés » (`instance` lu comme un code).

## Objective

Qu'à l'entrée, le médecin soit orienté vers le bon écran — et vers un écran de panne avec réessai quand le service est indisponible — et que chaque action sur ses messageries (rattacher, détacher, définir par défaut, ré-essayer l'authentification) dise si elle a réussi et, sinon, pourquoi.

### Périmètre

1. **Entrée** : `initialize()` distingue « erreur » de « zéro boîte » ; écran de panne avec réessai ; un `Client-Session-Id` est tiré dès l'entrée ; le 409 de non-concordance session/boîte est traité explicitement.
2. **« Ré-essayer l'authentification »** : une vraie sonde (réutiliser celle du rattachement) qui fait repasser la boîte `Active` en cas de succès, et affiche l'erreur sinon.
3. **Gestion des comptes** : chaque action teste son résultat, affiche le motif, et ne poursuit (bascule, déconnexion) que sur succès.
4. **Messages d'erreur du rattachement** : `instance` lu comme un code seulement s'il en a la forme ; `detail` prioritaire sur les 409 ; libellé pour `PSC_SESSION_REQUIRED`.

## Definition of Done

- [ ] Build et tests verts : weda2, api-mail
- [ ] Test d'intégration de bout en bout pour la sonde de ré-authentification d'une boîte `AuthFailing` (route existante ou ajoutée) : sur login réussi la boîte repasse `Active` dans la réponse ; sur refus elle reste `AuthFailing` avec un code lisible, vu rouge (règle 1b)
- [ ] Tests unitaires et de store rouges d'abord :
  - [ ] chargement des boîtes en 503 : écran de panne, pas « PSC requis » ni onboarding
  - [ ] DELETE de détachement en 500 : pas de déconnexion, message affiché, la boîte reste listée
  - [ ] 409 « déjà rattachée » : le `detail` du serveur s'affiche ; 401 `PSC_SESSION_REQUIRED` : libellé dédié
- [ ] Scénario E2E-MAILBOX-002 « api-mail indisponible à l'entrée : écran de panne puis réessai » ajouté (angular `requis` ; mobile : `requis` si le mobile a le même écran d'entrée, à confirmer au `/start`)
- [ ] Aucune adresse ni identifiant de session ajouté aux journaux

## Manual Test Plan

1. Arrêter api-mail, ouvrir weda2 → écran « service indisponible » avec « Réessayer » ; relancer api-mail, réessayer → la boîte s'ouvre.
2. Boîte en échec d'authentification (mot de passe ou jeton refusé côté banc) : rétablir l'accès, cliquer « Ré-essayer l'authentification » → la boîte redevient utilisable.
3. Détacher sa dernière boîte avec api-mail en erreur → message d'erreur, pas de déconnexion.
4. Rattacher une boîte déjà rattachée → « Cette messagerie est déjà rattachée ».

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : PSC / e-CPS ; l'écran « PSC requis » n'est plus montré à tort ; la sonde de ré-authentification passe par XOAUTH2 avec le jeton PSC de la session
- **Habilitations** : rattachement validé par l'opérateur MSSanté (inchangé, task-308)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : rattachement, détachement et ré-authentification tracés comme aujourd'hui (réussite et échec)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable — aucune DSCP manipulée
- **AIPD / impact RGPD** : inchangé
