# todo-task-381.md — Un refus métier d'api-mail s'affiche une seule fois, avec son vrai motif

**Repos**: client-angular
**Dependencies**: — (aucune). task-370 (intercepteurs d'authentification et d'erreur) est archivée.
**Epic**: E009
**Single frontend**: true
**Priorité**: **3** — messages contradictoires : un « Accès refusé » ou « Service temporairement indisponible » générique s'ajoute au motif réel qu'affiche l'écran MSS.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-68** ; ANG-72 corrigé depuis, voir plus bas).

## Ce qui est établi

> **Revérifié le 2026-11-01** sur weda2 `feature/nova-mss-weda-integration` (`10e55c09`, après le rebase sur
> `next` Angular 22). Les numéros de ligne ci-dessous sont ceux de cette révision.

- **ANG-68 — toujours présent.** `apps/weda2/src/app/core/interceptors/error.interceptor.ts:86-132`
  (`handleTechnicalError`) notifie **tout** 5xx (« Service temporairement indisponible. Veuillez patienter. ») et
  **tout** 403 (« Accès refusé. Vous n'avez pas les permissions nécessaires. »), sans regarder qui répond ni ce que
  dit la réponse. Or api-mail rend ses refus métier en problem+json avec un `code` (`GlobalExceptionHandler.cs:79`),
  que le module MSS lit et explique lui-même. Le médecin reçoit donc deux messages, dont un générique qui peut
  contredire le premier. Cas concrets :
  - 403 `MAILBOX_PSC_MISMATCH`, `MAILBOX_ACCESS_REFUSED`, `MAILBOX_NOT_ATTACHED`, `MAILBOX_PSC_SESSION_REQUIRED` ;
  - 503 `MAIL_SERVER_UNAVAILABLE`, et 503 `MAIL_DELIVERY_UNCERTAIN` (task-376 : la rédaction dit « ce message est
    peut-être parti », le toast dit « service indisponible ») ;
  - 503 du proxy PSC, refus d'auteur de task-367.
- **Le mécanisme d'exclusion existe déjà** : le jeton `SILENT_HTTP_ERRORS`
  (`apps/weda2/src/lib/auth/models/silent-http-errors.token.ts`, task-365) coupe la notification d'une requête
  marquée. Aucune requête MSS ne le porte aujourd'hui.
- **Les requêtes vers api-mail sont reconnaissables** : `mss-headers.interceptor.ts:34-36` les identifie par
  `request.url.startsWith(MSS_API_URL)`.
- **Contournement existant** : `libs/mss/src/features/mailbox-management/mss-mailbox-management.component.ts:436-441`
  évite `reload()` au détachement de la boîte par défaut, en partie pour ne pas déclencher deux toasts « Accès
  refusé ». Il a une **seconde raison**, indépendante : le résultat de ces deux appels serait jeté par la
  déconnexion qui suit. Il reste donc en place ; seul son commentaire est à mettre à jour.
- **ANG-72 — corrigé par task-417 (archivée le 2026-10-30).** L'accusé de lecture repose désormais sur
  `FolderType.Sent` (`isSentFolder` dans `libs/mss/src/core/utils/read-receipt.util.ts`), avec un test sur un dossier
  « Consent ». Hors périmètre de cette task.

## Objective

Qu'un refus métier d'api-mail soit annoncé **une seule fois**, par l'écran qui sait l'expliquer, sans retirer la
notification générique des erreurs que personne d'autre n'explique.

### Périmètre

1. **`errorInterceptor`** : pas de notification générique pour une réponse d'**api-mail** (URL sous `MSS_API_URL`)
   dont le corps est un problem+json portant un `code`. Le module MSS s'en charge.
2. **Inchangé** : la notification générique reste pour un 403 / 5xx sans `code` (passerelle, panne réseau, autre
   service que api-mail) et pour toute réponse d'un autre service, même porteuse d'un `code`.
3. **Commentaire** du contournement de `mss-mailbox-management` mis à jour : il ne cite plus le toast comme raison.

## Definition of Done

- [ ] Build et tests weda2 verts
- [ ] Tests unitaires de `errorInterceptor`, rouges d'abord :
  - [ ] 403 `MAILBOX_PSC_MISMATCH` d'api-mail : aucune notification générique
  - [ ] 503 `MAIL_DELIVERY_UNCERTAIN` d'api-mail : aucune notification générique
  - [ ] 503 d'api-mail **sans** `code` (corps vide ou HTML de passerelle) : la notification générique reste
  - [ ] 403 **avec** `code` d'un autre service que api-mail : la notification générique reste
  - [ ] requête marquée `SILENT_HTTP_ERRORS` : toujours aucune notification (non-régression task-365)
- [ ] Le motif MSS reste affiché : test du composant qui lit `MAILBOX_PSC_MISMATCH` inchangé et vert
- [ ] Aucune donnée de santé ajoutée aux journaux

## Manual Test Plan

1. Lancer api-mail (AppHost) et weda2 (`npm start` dans `Client/Angular/front`).
2. Provoquer un 403 `MAILBOX_PSC_MISMATCH` (carte d'un autre praticien sur la boîte) → un seul message, celui de
   l'écran MSS ; aucun toast « Accès refusé ».
3. Arrêter le serveur de messagerie (ou couper IMAP via Toxiproxy) et ouvrir la boîte → le message MSS de panne
   seul ; aucun toast « Service temporairement indisponible » en plus.
4. Arrêter api-mail entièrement (aucun problem+json) → le toast générique apparaît, comme aujourd'hui.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée ; le motif d'un refus PSC est affiché sans contradiction
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable
- **AIPD / impact RGPD** : inchangé
