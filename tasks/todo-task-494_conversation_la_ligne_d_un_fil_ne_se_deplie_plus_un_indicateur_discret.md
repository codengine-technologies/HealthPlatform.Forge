# todo-task-494.md — En mode Conversation, la ligne d'un fil ne se déplie plus : un indicateur discret

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: task-487
**Epic**: E024

> Demande humaine du 2026-11-22 : « Depuis la mise en place de la vue conversation, […] il n'y a plus d'intérêt à
> afficher les mails de la conversation dans la liste des emails. Un indicateur suffit mais il devrait être discret,
> et le fait que les emails s'affichent en dessous devrait disparaître. »
>
> Arbitrages de l'humain, le même jour :
> - **clients** : weda2 et mobile ;
> - **agir sur un seul message d'un fil** : le **mode Liste suffit**. Rien n'est ajouté à la vue chat ; pour supprimer,
>   ranger ou rattacher un message précis, le praticien repasse en mode Liste ou ouvre le dossier du message
>   (Envoyés…).

## Objectif

En mode Conversation, une ligne de la liste représente un fil entier, et la sélectionner ouvre déjà la vue chat
avec tous ses messages (task-487). Le chevron qui déplie les messages du fil sous la ligne les montre une seconde
fois, moins lisiblement, au prix d'une requête et de lignes « enfants » qui gênent la sélection, le glisser-déposer
et les actions au survol. On le retire. La ligne garde un **indicateur discret** du nombre de messages, et elle
**ne cache plus un message non lu** : tant qu'un message du fil est non lu dans le dossier affiché, elle est en gras.

### Ce qui est établi

- **Le mode Conversation** (`MailViewMode.Conversation`) n'affiche que la « feuille » de chaque fil : le message le
  plus récent du fil **dans le dossier listé** (`IsThreadRoot`, calculé par
  `OnlineMailDataProvider.ApplyThreadFlags` avec `GetLatestMessageIdsPerThreadAsync(…, folderPath)`). Les messages
  plus anciens du fil sont masqués de la liste et n'apparaissent qu'en dépliant.
- **Le nombre affiché** est `MailDto.ThreadCount`, compté par `MailRepository.GetThreadCountsAsync` sur le fil entier
  (tous dossiers). Les deux clients ne le transmettent à la ligne qu'en mode Conversation (`threadCountFor`).
- **Le dépliage** : weda2 `MailStateService.expandThread` / `threadChildren`, mobile `MailListComponent.onToggleThread`
  / `MailStateService.expandThread`. Les deux appellent `GET /api/v1/mail/thread/{messageId}` et rendent des lignes
  enfants (`mail-list-row-thread-child` sur weda2) sous la ligne du fil, libellé « N messages » + chevron
  (`mail-list-row-thread-count`, `mail-list-row-thread-toggle`).
- **Le gras de la ligne** est l'état lu du seul message affiché. Aucun champ de la liste ne dit qu'un message plus
  ancien du fil, masqué derrière la ligne, est non lu (`grep IsRead|Unread OnlineMailDataProvider.cs` : rien). Une
  fois le dépliage retiré, ce message serait **invisible** : c'est la seule perte à compenser.
- **La vue chat** marque lus les messages reçus du fil qu'elle ouvre (E2E-CONV-001). « Lire le message complet »
  n'apparaît que sur une bulle coupée (message long) : ce n'est pas un accès général à chaque message, et l'humain a
  choisi de ne pas en ajouter.
- **api-mcp** n'appelle pas la route du fil (`grep thread Api/Mcp/src` : rien hors binaires).

### Règles

1. **En mode Conversation, la ligne d'un fil ne se déplie plus** : plus de chevron, plus de lignes enfants, sur weda2
   et sur mobile. Sélectionner la ligne ouvre la vue chat, comme aujourd'hui (E2E-CONV-003).
2. **Indicateur discret** : à la place de « N messages » et du chevron, un petit chiffre en couleur secondaire avec
   une icône de bulle, à côté de l'objet. Son libellé accessible (survol sur weda2, lecteur d'écran sur les deux) dit
   « N messages ». Il n'apparaît que pour un fil d'au moins deux messages.
3. **Le chiffre est le nombre de messages du fil entier**, tous dossiers (le `ThreadCount` d'aujourd'hui), y compris
   dans une vue filtrée (tag, « À traiter », « Pour moi », recherche) : c'est le fil entier que la vue chat ouvre.
4. **La ligne est en gras tant qu'un message du fil est non lu dans le dossier affiché**, même si le message affiché
   par la ligne est lu. Ouvrir le fil en vue chat lit ses messages reçus : la ligne perd son gras.
5. **Le compteur de non-lus du dossier ne change pas** : il compte toujours des messages, pas des fils.
6. **Le mode Liste ne change pas** : une ligne par message, sans indicateur de fil.
7. **Agir sur un seul message du fil** (supprimer, ranger, étiqueter, rattacher) se fait en mode Liste, ou depuis le
   dossier du message. Les actions de la ligne en mode Conversation gardent leur portée d'aujourd'hui.

### Hors périmètre

- La route `GET /api/v1/mail/thread/{messageId}` reste en place. Si plus aucun client ne l'appelle après cette task,
  son retrait sera une task séparée (règle d'or 6), après vérification de tous ses consommateurs.
- La portée des actions de ligne en mode Conversation (une action sur la ligne vise-t-elle le fil entier ?) n'est pas
  modifiée ici ; task-493 traite le cas de « Traité ».
- Aucun lien « Ouvrir ce message » n'est ajouté aux bulles de la vue chat (arbitrage humain du 2026-11-22).

## Definition of Done

- [ ] Build passes : api-mail, dtos-mss, `nx build weda2`, client-mobile (0 erreur).
- [ ] Tests pass : api-mail, `nx test mss-lib`, `nx test weda2`, client-mobile (0 échec).
- [ ] Tests unitaires (api-mail) de la règle « un message du fil non lu dans le dossier » : message affiché non lu,
      message plus ancien non lu derrière une feuille lue, tous lus, message non lu du fil dans un autre dossier (ne
      compte pas), message hors fil ; chacun vu rouge.
- [ ] Test d'intégration de bout en bout pour la liste d'un dossier (`GET` de la page de la boîte de réception) : sur
      un fil de trois messages reçus dont le plus ancien est non lu et les deux autres lus, la ligne du fil (la
      feuille) porte, relu dans la réponse réelle, « un message du fil est non lu » et `threadCount` = 3 ; après
      lecture du plus ancien, le même champ est faux. Cas d'échec : un message non lu du fil rangé dans un autre
      dossier ne met pas la ligne en non lu. Vu rouge (règle 1b).
- [ ] dtos-mss : le champ ajouté au contrat de la liste est publié et api-mail bumpé ; `contract_impact.py check` sans
      impact non adapté (ajouter un champ n'en est pas un).
- [ ] Tests de composant weda2 et mobile, chacun vu rouge :
  - en mode Conversation, une ligne de fil n'a ni chevron ni ligne enfant, et montre l'indicateur avec le libellé
    accessible « N messages » ;
  - la ligne est en gras quand le contrat dit qu'un message du fil est non lu, même si son message est lu ;
  - en mode Liste, aucun indicateur.
- [ ] Le code de dépliage est retiré des deux clients (état, appels à la route du fil, lignes enfants, styles), sans
      code mort laissé derrière ; plus aucun appel client à `GET /api/v1/mail/thread/{messageId}`.
- [ ] `data-testid` sur l'indicateur ; aucun texte en dur hors de la convention de chaque client.
- [ ] Mobile : référence Stitch de l'écran de liste mise à jour (`/stitch-design`, best-effort).
- [ ] Scénario **E2E-CONV-004** (version 1, `mobile: requis`, `angular: requis`) ajouté à
      `Api/Mail/e2e/scenarios.yml` et implémenté dans les deux clients : le test dépose, comme un autre logiciel, un
      fil de trois messages d'un confrère dans la boîte de réception, le plus ancien non lu, les deux autres lus. En
      mode Conversation, la liste montre **une** ligne pour ce fil, en gras, avec l'indicateur « 3 messages » ; aucun
      chevron, aucune ligne enfant. Le praticien sélectionne la ligne : la vue chat montre les trois messages ; de
      retour à la liste, la ligne n'est plus en gras, et relu du serveur, les trois messages sont lus.
- [ ] Scénario **E2E-MAIL-006** passé en **version 2** (`angular: requis`, mobile inchangé : non-applicable, pas de
      glisser-déposer) : le praticien n'atteint plus le message envoyé en dépliant le fil, il ouvre **Envoyés en mode
      Liste** et glisse le message envoyé sur la Corbeille. Relu du serveur : la suppression vise Envoyés, le message
      envoyé a quitté Envoyés, et le message de même numéro de la boîte de réception y est toujours.
- [ ] E2E-CONV-001 et E2E-CONV-003 : leur attendu ne change pas ; leur implémentation, qui attend le libellé
      `mail-list-row-thread-count` pour savoir que le fil est formé, lit le nouvel indicateur. Rejoués verts par
      `/e2e`.
- [ ] Aucune donnée de santé dans les journaux ni dans le libellé de l'indicateur (il ne cite que le nombre).

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil de développement habituel).
- weda2 : `cd Client/Angular/front && npm run start:weda2`, ouvrir la messagerie.
- Mobile : `cd Client/Mobile && npm start`, ouvrir la boîte.
- Données : depuis une autre boîte, envoyer à la boîte de test un message M1, puis M2 en réponse à M1, puis M3 en
  réponse à M2.

1. weda2, Boîte de réception, mode Conversation : le fil M1-M2-M3 tient sur **une** ligne, avec un petit chiffre
   « 3 » et une icône de bulle à côté de l'objet ; au survol, « 3 messages ». Aucun chevron.
2. Passer en mode Liste, ouvrir M2 et M3 (ils deviennent lus), laisser M1 non lu. Revenir en mode Conversation : la
   ligne du fil est **en gras** alors que M3, le message affiché, est lu.
3. Sélectionner la ligne : la vue chat montre M1, M2 et M3. Revenir à la liste : la ligne n'est plus en gras.
4. Ouvrir la puce « À traiter » (ou un tag posé sur M3) en mode Conversation : l'indicateur dit toujours « 3 ».
5. Passer en mode Liste : trois lignes, sans indicateur. Glisser M1 sur la Corbeille : seul M1 part.
6. Refaire 1 à 3 sur le mobile (le libellé « 3 messages » est lu par le lecteur d'écran).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du cabinet).
- **Vague Ségur** : hors Ségur — présentation de la liste des messages déjà reçus, aucune exigence DSR nouvelle.
- **Exigences DSR honorées** : non applicable — aucun échange ni document nouveau.
- **INS** : non applicable — aucun patient manipulé ni identifié.
- **Authentification PS** : inchangée — session PSC (e-CPS) de la messagerie.
- **Habilitations** : inchangées. Titulaire, délégataire et membre voient la liste comme aujourd'hui ; un délégataire
  ou un membre sans verdict récent de l'opérateur ne voit rien (règle 14). L'état lu reste celui de la boîte.
- **Interop CI-SIS** : non applicable — le fil est lu des en-têtes MSSanté standard (`Message-ID`, `In-Reply-To`,
  `References`), aucun document CDA produit.
- **Tracé PGSSI-S** : inchangé — la lecture d'un message, y compris par la vue chat, est tracée comme aujourd'hui au
  nom de la personne réelle (règle 14). Afficher un indicateur n'est pas un acte. Conservation inchangée : famille
  `HealthDataAccess`, 3 653 jours.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui — l'état lu est celui de la base de la boîte, environnement HDS existant ; aucune donnée
  de santé nouvelle (un booléen dérivé de l'état lu).
- **AIPD / impact RGPD** : inchangée — même traitement, présentation différente.
