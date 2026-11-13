# todo-task-475.md — Angular : rédaction fiable et session de boîte étanche

**Repos**: client-angular, api-mail
**Dependencies**: aucune
**Epic**: E025
**Priorité**: EPIC E025, issue de l'audit du 2026-11-12/13, validée par l'humain le 2026-11-13.

> **Origine.** Audit en lecture seule du 2026-11-12/13 (agents « bugs Angular », « sécurité Angular »). La rédaction
> liée à la vie du composant a été relue dans le code par l'orchestrateur le 2026-11-13.
>
> **api-mail** n'est listé que pour le catalogue des scénarios e2e (`Api/Mail/e2e/scenarios.yml`).
>
> **Note de lot.** La task « Angular : pannes visibles, listes justes » (widgets et frise qui avalent les pannes,
> pagination non recomplétée, étiquette appliquée au mauvais mail, marquage « lu » annulé, écritures muettes…) a été
> présentée et **passée** par l'humain le 2026-11-13 : elle n'est pas écrite.

## Ce qui est établi

Lecture du code au 2026-11-13 (`Client/Angular/front`) :

### Rédaction (`libs/mss/src/features/mail/components/mail-compose/`)

- **Envoi lié à la vie du composant.** `mail-compose.component.ts:1675` :
  `sendObs.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(…)` ; même chose `:1623` pour l'envoi d'un brouillon.
  Le médecin clique « Envoyer » puis aussitôt « Tableau de bord » ou bascule de boîte : le composant est détruit, la
  requête annulée, aucun « envoyé » ni « échec » ne s'affiche ; le message est parti, ou pas, selon l'instant. Le
  danger est connu ailleurs : `features/pending-sends/mss-pending-sends.component.ts:467-471` (« se désabonner d'une
  requête HTTP l'annule… »).
- **Rédaction perdue en quittant.** `libs/mss/src/index.ts` : seule la route `contacts` a un `canDeactivate` (`:107`),
  pas `mail` ; seul `beforeunload` protège (`mail-compose.component.ts:735-741`). La bascule de boîte ne solde que les
  suppressions différées (`core/stores/mailbox-session.store.ts:538-541`). Une rédaction de moins de 30 s (ou dont
  l'enregistrement automatique a échoué) disparaît sans question.
- **Fermeture différée qui ferme la rédaction suivante.** `:1633`, `:1642`, `:1700` :
  `setTimeout(() => this.doClose(), 1500 | 4000)`, jamais annulé, sans contrôle de `composeSession`. Le médecin ouvre
  une nouvelle rédaction dans le délai : elle est fermée et remise à zéro, sans enregistrement.
- **Brouillon écrasé.** `:1924-1930` : `currentDraftId.set(draftId)` est posé avant la réponse de `getDraft`, sans
  branche `error`. Le chargement échoue, la rédaction s'ouvre vide, le médecin tape : l'enregistrement remplace le vrai
  brouillon (destinataires, pièces, texte).
- **Suggestions de destinataires dans le désordre.** `:1066-1082` : une souscription par frappe, sans temporisation ni
  annulation. Les résultats de « mar » arrivent après ceux de « martin » : risque de choisir un homonyme dans une liste
  périmée. Le formulaire de recherche le fait correctement (`mail-search.component.ts`, `switchMap`).
- **Éditeur.** `ui/html-editor/html-editor.component.ts:77-79` ne consomme `skipNextSync` que si l'entrée change ;
  `:393-401` (`toggleSourceMode`) l'arme même quand le HTML réémis est identique. Après un aller-retour en mode
  source, un changement de signature (`mail-compose.component.ts:2376-2393`, `body.set` sans `setHtml`) n'est pas
  affiché mais part dans le message.
- **Citation qui charge les contenus distants.** `core/utils/quoted-body.util.ts:97-98` rend `content.bodyHtml` tel
  quel ; `mail-compose.component.ts:1861` le pose dans l'éditeur ; `html-editor.component.ts:102` accepte toute image.
  `blockRemoteContent` n'est appliqué qu'à la lecture : Répondre ou Transférer charge le pixel de pistage, qui repart
  dans la réponse.

### Session de boîte

- **Suspension bloquée par une garde de sortie.** `core/services/mailbox-access-suspension.service.ts:45-52` purge
  puis navigue vers l'écran « accès suspendu » ; `features/contacts/mss-contacts.component.ts:993-1005` (`canLeave`)
  peut refuser : le carnet reste affiché après la révocation, la génération n'avance pas.
- **Requête d'écriture qui change de boîte.** `apps/weda2/src/app/core/interceptors/mss-headers.interceptor.ts:53-57` :
  `pinned?.email ?? mailboxSession.currentEmail()`. L'intercepteur d'authentification est le premier de la chaîne
  (`lib/auth/interceptors/utils/auth-interceptor.utils.ts`, `refreshAndReplay`) : une écriture qui attend un
  rafraîchissement repasse par les en-têtes MSS après la bascule et vise le mail de même UID de l'autre boîte. Seule la
  suppression annulable fige sa boîte (`MSS_MAILBOX_PIN`).
- **Flux de l'assistant IA en `fetch` brut.** `core/services/mss-api.service.ts:2361-2397` reconstruit les en-têtes à
  la main et lève `new Error("SSE request failed: …")` : un 403 `MAILBOX_ACCESS_*` ne déclenche pas la suspension, un
  jeton échu n'est pas rafraîchi.
- **API reconnue par préfixe.** `mss-headers.interceptor.ts:36` : `request.url.startsWith(mssApiUrl)`.
  `https://mss-api.exemple.fr.evil.tld/…` passerait (aucun appel actuel ne l'exploite).
- **Déconnexion.** `MailboxSessionStore.clear()` n'est appelé que par `mss-mailbox-management.component.ts:446`, `:466` ;
  `core/guards/mailbox.guard.ts:253` laisse passer dès que `current()` est posé. Le cloisonnement entre deux personnes
  repose sur un rechargement mémorisé en `sessionStorage`, qui rend `null` si le stockage est indisponible.
- **Notifications.** `core/components/notification-dispatcher/notification-dispatcher.component.ts:108-126` : la file
  appartient au composant, monté une fois ; elle n'est pas vidée à la bascule. `new Notification(payload.title,
  { body: payload.body })` (`:121`) affiche titre et contenu hors de l'application, lisibles session verrouillée.
- **`nginx.conf`** (`:43-53`) : la seule directive CSP est `frame-ancestors` ; le bloc des statiques pose son propre
  `add_header` et perd donc `nosniff` ; `X-XSS-Protection` est obsolète ; pas de `Referrer-Policy` ni de
  `Cache-Control` sur `index.html`.
- **Application autonome `apps/mss`.** `environments/environment.prod.ts:3` pointe sur l'API de dev ;
  `app/app.config.ts:14-24` ne fournit ni `MSS_ACCESS_TOKEN`, ni `MSS_USER_EMAIL`, ni `MSS_RESETTABLE_STORES`
  (`NullInjectorError` dès la liste de mails, purge de bascule sans effet). Huit navigations codent `'/messagerie'` en
  dur au lieu de `MSS_MODULE_PREFIX`.

## Objective

Un envoi lancé aboutit et le médecin en voit l'issue ; une rédaction n'est jamais perdue ni écrasée en silence ; ce
qui appartient à une boîte ou à une personne ne survit ni à une bascule, ni à une suspension, ni à une déconnexion.

Règles :

1. **Un envoi lancé survit à la vie de l'écran**, et son issue s'affiche toujours (notification si l'écran a changé).
2. **Quitter une rédaction non enregistrée demande confirmation.** La bascule de boîte l'enregistre d'abord, comme
   elle solde les suppressions différées.
3. **Une rédaction ne réagit qu'aux réponses de sa propre session.**
   - La fermeture différée est annulée à la réinitialisation de la rédaction.
   - Un brouillon n'est adopté qu'après lecture réussie ; sinon l'échec s'affiche et la rédaction se ferme.
   - Les suggestions sont temporisées et annulées par la frappe suivante.
   - L'éditeur compare les contenus au lieu de sauter « la prochaine » mise à jour.
4. **La citation bloque les contenus distants**, comme la lecture (`blockRemoteContent`).
5. **Suspension** : l'écran routé est détruit sans passer par une garde de sortie.
6. **Toute requête d'écriture fige sa boîte au moment du geste**, avant tout rafraîchissement de jeton. Le flux de
   l'assistant IA lit le `ProblemDetails`, déclenche la suspension et rafraîchit le jeton.
7. **L'API est reconnue par son origine exacte** (`new URL(…).origin`).
8. **Déconnexion et changement de personne** vident la session de boîte, indépendamment du rechargement. La file de
   notifications est vidée à chaque changement de génération ; la notification système dit seulement « Nouveau
   message ».
9. **`nginx.conf`** : CSP `default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'self'; frame-src blob:`
   (complétée des hôtes requis, sans `unsafe-eval`) ; en-têtes de sécurité répétés sur les statiques ;
   `Referrer-Policy` ajoutée, `X-XSS-Protection` retiré ; `index.html` non mis en cache.
10. **`apps/mss`** : cible de production retirée, ou fournie avec les mêmes jetons que weda2 ; toute navigation passe
    par `MSS_MODULE_PREFIX`.

### Hors périmètre (action humaine)

- Remplacer le joker `https://*.weda.fr` par la liste exacte des origines de Weda, dans `embeddedHostOrigins`
  (configuration de production de weda2) et dans `frame-ancestors` (`nginx.conf`). Une faille XSS ou une reprise de
  sous-domaine sur n'importe quel `*.weda.fr` suffit aujourd'hui à devenir « l'hôte » du pont `postMessage`.

## Definition of Done

- [ ] Tests de composant, d'intercepteur et de service, vus rouges par mutation :
      - envoi qui survit à la destruction de la rédaction, issue affichée ;
      - confirmation en quittant une rédaction non enregistrée ; enregistrement avant bascule ;
      - fermeture différée annulée ; brouillon en échec non adopté ; suggestions dans l'ordre de la frappe ; signature
        affichée après un aller-retour en mode source ;
      - citation sans contenu distant ;
      - suspension qui passe la garde du carnet ;
      - écriture figée sur sa boîte malgré une bascule pendant le rafraîchissement ;
      - flux IA : 403 de suspension et jeton échu ;
      - intercepteur : une URL au préfixe trompeur ne reçoit ni en-têtes MSS ni `withCredentials` ;
      - déconnexion qui vide la session de boîte ; file de notifications vidée à la bascule ; notification système
        neutre ;
      - navigations par `MSS_MODULE_PREFIX`.
- [ ] **Scénario e2e** `E2E-COMPOSE-008` v1 ajouté à `Api/Mail/e2e/scenarios.yml` : « quitter l'écran pendant l'envoi :
      le message part une fois et son issue s'affiche ; quitter une rédaction non enregistrée demande confirmation ».
      Angular requis ; mobile **non-applicable** — la rédaction mobile est une fenêtre modale qu'on ne quitte pas sans
      la fermer.
- [ ] Trou du filet : scénario `E2E-COMPOSE-008` prouvé rouge sur le code non corrigé, ligne ajoutée dans
      `conventions/e2e.md`.
- [ ] weda2 démarre, se connecte, lit et envoie sous la nouvelle CSP : voie e2e Angular (`npm run e2e:mss`) verte.
- [ ] Prévention (règle d'or) : `conventions/angular.md` — « une écriture ne se lie jamais à la vie d'un composant
      qui peut disparaître » ; « une requête d'écriture fige sa boîte au geste » ; « l'API se reconnaît par son
      origine, jamais par un préfixe de chaîne » ; « une citation passe par `blockRemoteContent` ».
- [ ] Aucune donnée de santé dans les journaux du navigateur ni dans une notification système ; `data-testid` sur
      chaque élément interactif ajouté.
- [ ] Build et tests verts : weda2 (`nx build weda2`, `nx test weda2`, `nx test mss-lib`), lint du module.
- [ ] client-angular : code-only, aucun commit.

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail/src/AppHost && dotnet run`) et weda2 (`cd Client/Angular/front && npm start`).
2. Rédiger un message, cliquer « Envoyer » puis aussitôt « Tableau de bord » : le message part une fois (dossier
   Envoyés) et une notification annonce l'issue.
3. Rédiger sans attendre l'enregistrement automatique, puis cliquer un lien du menu : une confirmation est demandée.
   Basculer de boîte avec une rédaction ouverte : elle est enregistrée en brouillon.
4. Envoyer, puis ouvrir aussitôt « Nouveau message » : la nouvelle rédaction reste ouverte.
5. Répondre à un mail porteur d'images distantes, onglet réseau ouvert : aucune requête externe.
6. Délégataire : modifier un contact sans enregistrer, retirer la délégation depuis le compte du titulaire : l'écran
   « accès suspendu » s'affiche, le carnet disparaît.
7. Se déconnecter, se reconnecter avec un autre compte : le sélecteur ne montre aucune adresse du compte précédent.
8. Vérifier les en-têtes de la page et d'un fichier `.js` servis par nginx : CSP, `nosniff`, `Referrer-Policy`.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — fiabilité de la rédaction et étanchéité de la session
- **Vague Ségur** : hors Ségur — correctif de fiabilité et de sécurité
- **Exigences DSR honorées** : non applicable — PGSSI-S (confidentialité du poste partagé, défense en profondeur)
- **INS** : non applicable
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel ; jeton rafraîchi aussi pour le flux de
  l'assistant
- **Habilitations** : suspension effective sur tout écran (règle 14) ; écriture imputée à la boîte du geste
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé côté serveur ; l'écriture part sur la boîte visée, donc la trace aussi
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable — client web ; aucune donnée persistée côté navigateur
- **AIPD / impact RGPD** : inchangée — la notification système ne montre plus de contenu
