# todo-task-476.md — Mobile : une liste montre ce qui existe, une panne se voit

**Repos**: client-mobile, api-mail
**Dependencies**: aucune
**Epic**: E025
**Priorité**: EPIC E025, issue de l'audit du 2026-11-12/13, validée par l'humain le 2026-11-13. Porte le seul constat
classé **critique** côté mobile (recherche puis retour).

> **Origine.** Audit en lecture seule du 2026-11-12/13 (agent « bugs mobile »). La recherche qui écrit dans l'état de la
> boîte de réception et la recherche de patients morte après une erreur ont été relues dans le code par
> l'orchestrateur le 2026-11-13. Le constat critique repose sur la lecture du code Ionic 8.8.12 : à reproduire sur
> appareil.
>
> **api-mail** n'est listé que pour le catalogue des scénarios e2e (`Api/Mail/e2e/scenarios.yml`).

## Ce qui est établi

Lecture du code au 2026-11-13 (`Client/Mobile/src/app`) :

- **Recherche puis retour.** `mail-search/mail-search.page.ts:49-70` écrit dans l'état partagé de la boîte de réception
  (`state.setSearchActive(true)`, `state.setEmails(emails)` ; `onSearchCleared` fait `setEmails([])`). La remise en état
  n'est que dans `inbox/inbox.page.ts:200-203` (`ionViewWillEnter`). `/mail-search` est poussée dans l'outlet racine ;
  au retour, l'outlet des onglets réactive la même vue et `StackController.transition` sort sur
  `leavingView === enteringView` : `ionViewWillEnter` de la page d'onglet ne se rejoue pas (le commentaire
  `inbox.page.ts:159-163` décrit déjà ce comportement pour la bascule). `hasMore` reste faux
  (`mail-state.service.ts:223-225`), `loadNextPage` sort aussitôt (`inbox.page.ts:484`). Écran : les résultats de
  recherche sous le titre du dossier, puis « Aucun mail dans ce répertoire » et « Fin de la liste » dans **tous** les
  dossiers, jusqu'à un aller-retour d'onglet. Même cause : `home/home.page.ts:65-76` ne recharge pas le tableau de bord
  au retour d'un mail ouvert depuis un widget.
- **Changement de dossier rapide.** `inbox.page.ts:103-111` lance `loadEmailsForFolder` sans annulation ; `:374-437` ne
  garde que la génération de boîte (`isStale`). `currentTagCode` est posé avant l'`await` (`:395`) ; la réponse lente
  d'INBOX, arrivée après celle d'un petit dossier, impose sa liste sous le titre du second ; si l'un est une étiquette,
  `getMailsByTag(étiquette de B, UID de A)` peut partir.
- **Recherche de patients.** `features/patient/components/patient-search/patient-search.component.ts:58-61` : le
  `catchError` est hors du `switchMap` ; à la première erreur, le flux se termine, plus rien n'écoute la saisie
  jusqu'au redémarrage (l'onglet est gardé vivant). `loadInitialPatients()` (`:113-122`) n'est pas annulé par une
  recherche.
- **Fiche patient.** `features/patient/components/patient-timeline/patient-timeline.component.ts:297`, `:312` :
  `catchError(() => of(vide))` affiche « Aucun document » pendant une coupure ; `:335-349` avance `currentPage` même
  sur échec : la page en échec est sautée pour de bon.
- **Assistant IA.** `features/mail/components/ai-chat/ai-chat.component.ts:116-160` : `createConversation` souscrit
  sans annulation ; `reset()` (`:462-475`) n'annule que le flux de réponse. Deux créations en vol (patient X, puis
  patient Y) : les deux résumés s'empilent, `conversationId` est celui de la dernière réponse ; les questions sur Y
  peuvent recevoir des réponses tirées des documents de X.
- **Temps réel.** `core/services/mail-events-stream.service.ts:84-129` et `notification-stream.service.ts:68-104` :
  aucun `onerror`, aucun écouteur de reprise d'application ni de réseau dans `src/app`. Après une veille, si la
  reconnexion automatique d'`EventSource` est refusée (jeton figé dans l'URL et expiré), le flux est fermé pour de bon ;
  les événements manqués ne sont jamais rattrapés.
- **Recherche de mails.** `features/mail/components/mail-search/mail-search.component.ts:130-137`, `:267-282` :
  `debounceTime` puis `subscribe`, sans `switchMap` ; `mail-search.page.ts:49-63` second étage non gardé. Le retour du
  détail restaure `lastResultEmails` (`:40-47`), copie d'avant la lecture ou la suppression. La puce « Aujourd'hui »
  envoie « maintenant − 24 h » (`mail-search.component.ts:328-330`).
- **Écritures liées à la vie de l'écran.** `features/mail/components/mail-detail/mail-detail.component.ts:164`
  (marquage lu), `:462-464` (accusé de lecture), `:884-886` et `:913-915` (étiquettes) : `takeUntilDestroyed` ; quitter
  l'écran annule la requête, sans retour arrière ni message.
- **Suppression différée.** `features/mail/services/mail-pending-delete.service.ts:168-174` :
  `catchError(() => of(undefined))` avale l'échec ; `undo()` (`:93-107`) appelle `state.addMailToList(mail)`, qui ne
  vérifie pas le dossier affiché (`mail-state.service.ts:410-414`) ; un rafraîchissement dans les 6 s fait revenir le
  mail encore présent côté serveur, puis il est supprimé : ligne fantôme.
- **Puce « Bio à acquitter ».** `inbox.page.ts:388` remet le filtre à `null` à chaque chargement ;
  `inbox-biology-ack-chip.component.ts:101-110` ne s'éteint que si le dossier change. Puce active, liste non filtrée ;
  `bioAckAutoActivate` n'est jamais remis à `false` : un second lien depuis l'accueil ne l'active pas.
- **Divers.** `patient-timeline.component.ts:460-485` : « Aujourd'hui » = moins de 24 h ; `inbox.page.ts:561-585` : si
  `getFolders()` échoue dans `onFolderGone`, le rafraîchissement ne se termine jamais ;
  `mail-list.component.html:19,27,33,141` : `track mail.uid` alors que l'identité est (dossier, UID) ;
  `core/utils/http-error.util.ts:98-108` : un statut 0 (requête jamais partie, sans réseau) est dit « peut-être parti »
  et bloque « Envoyer ».

## Objective

Sur mobile, réseau instable compris, la liste affichée est celle du dossier et de la boîte choisis ; une panne ne se
fait jamais passer pour « rien » ; une action n'est ni perdue ni appliquée ailleurs.

Règles :

1. **La recherche a sa propre liste** et ne touche jamais l'état de la boîte de réception. Une page d'onglet ne compte
   jamais sur `ionViewWillEnter` au retour d'une page poussée dans l'outlet racine (accueil compris).
2. **Toute réponse est vérifiée contre ce qui est encore affiché** avant d'être appliquée : dossier (séquence de
   chargement, `currentTagCode` et `currentFolderPath` posés ensemble après le contrôle), conversation IA, requête de
   recherche, génération de boîte.
3. **Une panne s'affiche « Indisponible — Réessayer »** (fiche patient, recherche de patients) ; une page n'avance que
   sur succès ; une erreur ne termine jamais un flux de saisie.
4. **Temps réel.** À la reprise de l'application et après une coupure, le flux est rouvert avec le jeton courant, puis
   le dossier affiché et les compteurs sont relus.
5. **Une écriture ne dépend pas de la vie de l'écran** (marquage lu, accusé de lecture, étiquettes) : elle est portée
   par un service racine, avec retour arrière et message en cas d'échec.
6. **Suppression différée.** Un échec réinsère le mail et le signale ; le lot en attente est soldé ou annulé au
   changement de dossier et au rafraîchissement ; une réinsertion n'a lieu que si le dossier du mail est celui affiché.
7. **Puce « Bio à acquitter ».** Son état actif a une seule source (l'état de la liste) ; chaque lien depuis l'accueil
   l'active.
8. **Divers.** « Aujourd'hui » vaut depuis minuit (recherche, frise) ; un rafraîchissement se termine toujours ; les
   listes sont suivies par (dossier, UID) ; un statut 0 sans réseau vaut « non parti ».

### Hors périmètre

- Les états « Indisponible » de la tuile et de la puce de biologie, la frise de biologie : task-467.
- La fenêtre de rattachement patient : task-468. La rédaction (brouillons, signatures, favoris) : task-469.
- Le jeton dans l'URL du flux : restreint côté serveur par task-471.

## Definition of Done

- [ ] Tests de composant et de service, vus rouges par mutation :
      - recherche puis retour : la boîte de réception garde son dossier, sa liste et son défilement ; l'accueil se
        recharge au retour d'un mail ;
      - deux changements de dossier rapides : la liste correspond au dossier sélectionné ;
      - recherche de patients vivante après une erreur ; chargement initial annulé par la recherche ;
      - fiche patient : état « Indisponible », page non sautée ;
      - assistant IA : la conversation d'un autre mail est ignorée ;
      - flux rouvert à la reprise de l'application, dossier relu ;
      - recherche de mails dans l'ordre de la saisie ; retour du détail sur l'état vivant ;
      - écritures du détail qui survivent à la destruction de la page, retour arrière sur échec ;
      - suppression différée : échec signalé, annulation dans le bon dossier, lot soldé au changement de dossier ;
      - puce « Bio à acquitter » : état unique, second lien qui l'active ;
      - « Aujourd'hui » depuis minuit ; rafraîchissement terminé sur échec ; statut 0.
- [ ] **Scénario e2e** `E2E-SEARCH-015` v1 ajouté à `Api/Mail/e2e/scenarios.yml` : « rechercher puis revenir : la boîte
      de réception retrouve son dossier et charge la suite au défilement ». Mobile requis ; angular **non-applicable** —
      sur le web, la recherche s'affiche dans la liste elle-même, sans page à quitter.
- [ ] Trou du filet : scénario `E2E-SEARCH-015` prouvé rouge sur le code non corrigé, ligne ajoutée dans
      `conventions/e2e.md`.
- [ ] Prévention (règle d'or) : `conventions/angular.md` — « une page d'onglet Ionic ne recharge jamais son état dans
      `ionViewWillEnter` au retour d'une page poussée » ; « une réponse se vérifie contre l'objet encore affiché » ;
      « jamais de `catchError` hors du `switchMap` d'un flux de saisie » ; « une écriture ne se lie jamais à la vie
      d'une page ».
- [ ] Aucune donnée de santé dans `console.*` ; `data-testid` sur chaque élément interactif ajouté.
- [ ] Build et tests verts : client-mobile (`npm run build`, `npm test -- --watch=false --browsers=ChromeHeadless`),
      lint.

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail/src/AppHost && dotnet run`) et le mobile (`cd Client/Mobile && npm start`, ou
   l'APK de dev sur appareil).
2. Ouvrir la loupe, rechercher « potassium », revenir : la boîte de réception affiche son dossier et charge la suite au
   défilement ; changer de dossier : la liste est juste.
3. Toucher INBOX puis aussitôt un petit dossier : la liste correspond au titre.
4. Passer en mode avion, rechercher un patient (échec affiché), rétablir le réseau, rechercher à nouveau : résultats.
5. Ouvrir une fiche patient en mode avion : « Indisponible — Réessayer », jamais « Aucun document ».
6. Verrouiller le téléphone dix minutes, injecter un mail, déverrouiller : le mail apparaît et la notification arrive.
7. Supprimer un mail, ouvrir un autre dossier dans les 6 s, toucher « Annuler » : le mail revient dans son dossier
   d'origine, pas dans celui affiché.
8. Depuis l'accueil, toucher « Bio à acquitter » deux fois de suite (retour entre les deux) : la puce est active et la
   liste filtrée les deux fois.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — fiabilité de l'affichage mobile
- **Vague Ségur** : hors Ségur — correctif de fiabilité
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable
- **Authentification PS** : inchangée — PSC (e-CPS) CIBA, eIDAS substantiel ; flux rouverts avec le jeton courant
- **Habilitations** : aucune donnée d'une boîte, d'un dossier ou d'un patient affichée sous un autre (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé côté serveur ; une écriture n'est plus annulée en quittant l'écran, sa trace aboutit
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable — aucune donnée de santé persistée sur l'appareil
- **AIPD / impact RGPD** : inchangée
