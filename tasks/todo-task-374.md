# todo-task-374.md — Changer de messagerie ne laisse rien de la précédente : actions en attente, écran, notifications et compteurs

**Repos**: client-angular, api-mail (catalogue e2e `Api/Mail/e2e/scenarios.yml` seulement)
**Dependencies**: — (aucune). À coordonner avec task-365 (session partagée, empilement IMAP), qui touche au même `MailboxSessionStore`.
**Epic**: E016
**Single frontend**: true
**Priorité**: **1** — après un changement de messagerie, une suppression part sur un mail de l'autre boîte ; embarqué dans Weda, l'écran mêle les deux boîtes et les gestes portent sur d'autres messages que ceux affichés.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-10 ✔, ANG-11 ✔, ANG-25, ANG-27, ANG-77**).

## Ce qui est établi

- **Cause commune** : `MailboxSessionStore.switchTo` annonce un contrat (« les consommateurs réagissent à `switching` et `generation` »). **Aucun consommateur n'existe** : `generation()` n'est lu nulle part hors du store ; `MSS_RESETTABLE_STORES` n'enregistre que les deux services SSE.
- **ANG-10** — `mail-pending-delete.service.ts:56-78, 102-126` : une suppression « annulable » (6 s) ne fige pas sa boîte ; `mss-headers.interceptor.ts:44-51` lit la boîte courante à l'émission. Glisser vers la Corbeille puis changer de boîte : le mail de même UID de **l'autre boîte** part à la corbeille (définitivement si la source est la corbeille), celui de la première réapparaît.
- **ANG-11** — `mailbox-switcher.component.ts:152` navigue vers la même URL (`MSS_HOME_PAGE = 'mail'` en embarqué) sans `onSameUrlNavigation` : `MssMailComponent` et son état ne sont ni détruits ni purgés. Dossiers, liste, mail ouvert et rédaction restent ceux de A sous l'en-tête B ; le rafraîchissement ajoute les UID de B ; une réponse rédigée dans A part de B ; le temps réel est coupé.
- **ANG-25** — `notification-stream.service.ts` : pas de `?mailbox=` (le serveur retient la boîte par défaut) ; `reset()` coupe le flux pour de bon. En embarqué avec une boîte désignée ≠ défaut, les alertes « biologie anormale » de la boîte ouverte n'arrivent jamais.
- **ANG-27** — le compteur « N messages prêts à partir » est lu avant `open()` et jamais relu à la bascule : il compte ceux d'une autre boîte.
- **ANG-77** — `open()` sans fermeture ni purge quand une boîte est déjà ouverte ; bascules non sérialisées ; statut de connexion jamais relu.

## Objective

Que changer de messagerie **ferme proprement la précédente** — ses actions en attente sont exécutées dans **sa** boîte ou abandonnées — et **ouvre la suivante sur un écran neuf** : liste, dossiers, mail ouvert, rédaction, flux temps réel et compteurs sont ceux de la nouvelle boîte, en mode autonome comme embarqué.

### Périmètre

1. **Opérations différées figées sur leur boîte** : la boîte (et la session) est capturée à l'`enqueue` ; avant la bascule, les opérations en attente sont validées avec les en-têtes de la boîte sortante (ou abandonnées, avec retour visuel).
2. **Contrat du store respecté** : la vue mail est recréée sur `generation` (clé sur l'outlet ou navigation `reload`), les réponses d'une génération périmée sont ignorées, l'état mail est inscrit à la purge.
3. **Flux temps réel par boîte** : `?mailbox=` sur le flux de notifications ; flux rouverts à la fin de la bascule ; flux mail fermé à la destruction de la liste.
4. **Compteurs relus** à `open()` et `switchTo()`, remis à zéro à la purge.
5. **Bascules sérialisées** ; `open()` délègue à `switchTo` quand une boîte est déjà ouverte.

## Definition of Done

- [ ] Build et tests weda2 verts
- [ ] Tests unitaires et de store rouges d'abord :
  - [ ] suppression différée dans A, bascule vers B avant la fin : la requête part avec `Client-Email = A` (ou est abandonnée), jamais avec B
  - [ ] après la bascule, l'état mail (dossiers, liste, mail ouvert) est vide puis rechargé pour B ; une réponse de A arrivée après la bascule est ignorée
  - [ ] l'URL du flux de notifications porte `mailbox=` ; après la bascule, les deux flux sont rouverts pour B
  - [ ] le compteur d'envois en attente est relu après `open()` et `switchTo()`
  - [ ] deux bascules rapprochées : A fermée une fois, B ouverte une fois, dans l'ordre
- [ ] Scénario E2E-MAILBOX-001 « Changer de messagerie depuis l'écran mail, embarqué » ajouté (angular `requis` ; mobile : `requis` si le mobile offre le changement de boîte depuis la liste — à confirmer au `/start`), implémenté dans weda2 avec un praticien à deux boîtes : la liste est celle de B, une suppression faite juste avant n'atteint pas B
- [ ] Trou du filet : ligne dans `conventions/e2e.md` (le filet joue un praticien à une seule boîte)
- [ ] Aucune adresse ni identifiant de session ajouté aux journaux

## Manual Test Plan

1. Praticien à deux boîtes, Weda Échanges : glisser un mail de A vers la Corbeille, changer aussitôt de boîte vers B → aucun mail de B ne disparaît ; le mail de A est supprimé dans A (ou reste, avec un message).
2. Toujours embarqué, changer de boîte depuis l'écran mail → la liste, les dossiers et l'en-tête sont ceux de B ; aucun mail de A n'apparaît, même après 30 s.
3. Recevoir dans B (boîte non par défaut) un mail de biologie anormale → l'alerte s'affiche.
4. Laisser un message « prêt à partir » dans B, ouvrir A → le bandeau n'annonce pas le message de B.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif du socle multi-boîtes
- **Exigences DSR honorées** : non applicable — rétablit le cloisonnement entre boîtes (personnelle, organisationnelle)
- **INS** : non applicable
- **Authentification PS** : inchangée ; chaque boîte reste accédée sous la session PSC du praticien
- **Habilitations** : le cloisonnement par boîte (registre compte × adresse) est respecté côté client comme il l'est côté serveur
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : ouverture et fermeture de session de boîte tracées comme aujourd'hui (une fermeture par bascule)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé
