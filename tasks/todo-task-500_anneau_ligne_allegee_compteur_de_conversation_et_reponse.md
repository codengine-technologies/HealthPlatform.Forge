# todo-task-500.md — Anneau : une ligne allégée, le compteur de conversation et la réponse sur l'anneau

**Repos**: api-mail, client-angular, client-mobile
**Dependencies**: task-497
**Epic**: E027

> **Origine.** Demande humaine du 2026-11-27, en recette de task-497 (lot 1 de l'anneau, en PR) : la ligne de liste est
> trop chargée. « La mention « Non affecté » n'apporte rien » ; l'identifiant du message « doit uniquement s'afficher
> dans le hint au survol de l'anneau » ; le compteur de conversation doit être intégré à l'anneau « comme le fait
> Apple », et « x messages » retiré ; l'anneau doit aussi dire qu'un message a reçu une réponse, avec l'icône actuelle
> (lettre et flèche vers la gauche) placée au bord de l'anneau.
>
> **Décisions de l'humain, le même jour** :
> - les **deux clients** : weda2 et mobile ;
> - la pastille du compteur est **neutre, gris foncé**, pas rouge : en variante D, le rouge dit la gravité clinique
>   (biologie critique) ;
> - l'icône « répondu » va au bord de l'anneau **dès qu'une réponse existe**, que l'anneau soit ouvert ou fermé ;
> - **nouvelle task**, après task-497, qui se merge telle quelle.
>
> **Allègements complémentaires**, proposés par la forge après relecture des deux lignes et **validés par l'humain le
> 2026-11-27** (règles 8 à 14) : 2 valeurs de biologie au plus puis « +N » ; une seule date par ligne ; plus de
> « MESSAGE » / « COURRIER » ; « Envoyé » / « Brouillon » seulement hors de leur dossier ; sur le mobile, plus de puce
> « Biologie » en mode anneau, plus de code « (H) » / « (L) », « Document médical » en icône.

## Objectif

En tant que médecin qui parcourt sa boîte, je veux une ligne de liste qui ne dit que l'utile, et un anneau qui
rassemble l'état du message : avancement, gravité, à qui le tour, nombre de messages de la conversation, réponse
envoyée. Je lis la liste plus vite, sans perdre d'information.

### Ce qui est établi (code relu le 2026-11-27)

- weda2, `mail-header.component.html` :
  - la ligne écrit l'identifiant IMAP du message, `[uid]`, deux fois (squelette d'enrichissement et ligne enrichie),
    masqué au survol (`.mail-uid-debug`) ;
  - en mode anneau, elle écrit « Non affecté » (`mail-row-unassigned-{uid}`) ;
  - en vue conversation, « N messages » (`mail-list-row-thread-count`) suivi du bouton qui déplie le fil
    (`mail-list-row-thread-toggle`) ;
  - l'icône « répondu » (`mail-replied-{uid}`, icône `communication/mail-import-ou-lc`) a pour infobulle la phrase du
    bandeau (`replySummaryText`).
- Mobile, `mail-header.component.html` :
  - pas d'identifiant affiché ;
  - « Non affecté » (`mail-chip-unassigned-{uid}`) ;
  - la puce « N messages » (`mail-thread-{uid}`) est aussi le bouton qui déplie le fil ;
  - l'icône « répondu » (`arrow-undo`, `mail-replied-{uid}`) montre sa phrase à l'appui long.
- L'état en clair de l'anneau (task-497, règle 8) dit déjà « Non affecté. » : l'information reste au survol et pour le
  lecteur d'écran.
- Parcours e2e qui lisent ces éléments : E2E-RING-003 (« Non affecté » écrit sur la ligne), E2E-CONV-001, CONV-003 et
  SHARED-004 (présence du compteur pour reconnaître un fil), E2E-DETAIL-006 (présence de l'icône « répondu »).
- Aucun parcours e2e ne lit les éléments des règles 8 à 14 (valeurs de biologie de la ligne, dates, type, « Envoyé »,
  puces « Biologie » et « Document médical », codes d'interprétation) : seuls les tests de composant suivent.
- weda2 : `documentDate` retombe aujourd'hui sur la date d'envoi, d'où la même date écrite deux fois sur un message
  ordinaire ; `docTypeText` rend « MESSAGE » ou « COURRIER » sans document médical ; `flaggedBiologyResults` n'a pas de
  limite.

### Règles

1. **« Non affecté » quitte la ligne**, sur les deux clients. L'état en clair de l'anneau le garde (« Non affecté. »), au
   survol et pour le lecteur d'écran. Le tableau de bord (task-499) n'est pas concerné.
2. **L'identifiant du message quitte la ligne** (weda2). Il s'ajoute à l'**infobulle** de l'anneau, après l'état en
   clair : « … — Identifiant : 1234 ». Il n'entre **pas** dans le libellé lu par le lecteur d'écran. Ligne sans anneau
   (Envoyés, Brouillons, Corbeille, icône classique) : il va dans l'infobulle de l'initiale de l'expéditeur. Le
   squelette d'enrichissement ne l'écrit plus non plus. Le mobile n'affiche pas d'identifiant : rien à faire.
3. **Le compteur de conversation devient une pastille sur l'anneau**, en vue conversation, pour un fil d'au moins
   2 messages :
   - pastille ronde **gris foncé**, chiffre blanc (contraste ≥ 4,5:1), posée en haut à droite de l'anneau, à la
     manière des pastilles d'iOS ; au-delà de 99, « 99+ » ;
   - libellé accessible : « Conversation de N messages » ;
   - « N messages » quitte la ligne ;
   - weda2 : le bouton qui déplie le fil (chevron) reste à sa place ;
   - mobile : un appui sur la pastille déplie ou replie le fil, comme la puce aujourd'hui, sans ouvrir le message. La
     zone d'appui fait au moins 32 × 32 px, même si la pastille est plus petite. Le chevron de la puce disparaît ;
     l'état déplié se lit dans `aria-expanded` de la pastille.
4. **L'icône « répondu » se pose au bord de l'anneau** dès qu'une réponse existe, que l'anneau soit ouvert, fermé ou
   hors suivi :
   - même icône qu'aujourd'hui (lettre et flèche vers la gauche) dans une petite pastille blanche cerclée, en bas à
     droite de l'anneau ;
   - infobulle et libellé accessible : la phrase actuelle (« Vous avez répondu à ce message le … ») ;
   - l'icône quitte sa place dans la ligne.
5. **Ligne sans anneau** (Envoyés, Brouillons, Corbeille, icône classique) : elle reste celle d'aujourd'hui (règle 12
   de task-497), « N messages » et icône « répondu » à leur place. Seul l'identifiant passe dans l'infobulle de
   l'initiale (règle 2).
6. **Lisibilité à la taille de la liste (32 px)** : la pastille du compteur et celle de la réponse ne masquent ni les
   initiales du centre, ni l'extrémité de l'arc, ni le badge ⚠ de gravité. Elles débordent du cercle, sans changer la
   hauteur de la ligne. Aucune animation nouvelle.
7. **Identifiants de test conservés** : la pastille du compteur garde `mail-list-row-thread-count` (weda2) et
   `mail-thread-{uid}` (mobile) ; l'icône « répondu » garde `mail-replied-{uid}`. Les parcours qui reconnaissent un fil
   ou une réponse restent valides.

**Allègements complémentaires (validés le 2026-11-27)**

8. **Valeurs de biologie : 2 au plus sur la ligne**, les deux clients. Ordre : critiques d'abord, puis les autres
   anormales, dans l'ordre du compte rendu. Au-delà, une mention « +N autres » (libellé accessible : « N autres valeurs
   anormales, à lire dans le message »). Le détail du message montre toujours toutes les valeurs. La règle de
   task-392 ne change pas : seule la valeur signalée par le laboratoire est mise en évidence.
9. **Une seule date par ligne** (weda2). La date de réception reste en ligne 1. La date du document (ligne 3) ne
   s'écrit que pour un document médical dont la date diffère du **jour** de réception ; sinon, rien. Le repli actuel
   sur la date d'envoi disparaît.
10. **Plus de « MESSAGE » ni de « COURRIER »** (weda2) : le type ne s'écrit en ligne 1 que pour un document médical
    (BIOLOGIE, IMAGERIE, … ou DOCUMENT). Le badge « PATIENT » d'un message de patient ne change pas.
11. **« Envoyé » / « Brouillon » seulement hors de leur dossier** (weda2) : pas d'indicateur dans le dossier Envoyés (ou
    un de ses sous-dossiers) ni dans Brouillons, reconnus par leur type, jamais par leur nom (task-417). Il reste dans
    les vues mélangées : conversation, vue par étiquette, résultats de recherche.
12. **Mobile — plus de puce « Biologie » / « Biologie CRITIQUE » en mode anneau** : l'anneau (couleur de gravité), le
    badge ⚠ N et les valeurs la disent déjà. En icône classique, elle reste.
13. **Mobile — plus de code d'interprétation « (H) », « (L) »… après la valeur** : la flèche devant la valeur le dit. Le
    libellé accessible de la valeur garde le sens (« élevé », « bas », « critique »).
14. **Mobile — « Document médical » devient une icône** (document) sans texte ; « Document médical » et, s'il y a lieu,
    « version N » passent dans l'infobulle et le libellé accessible. La puce « À rattacher (N) » ne change pas.

### Hors périmètre

- Le grand anneau du détail et la section « Traitement » (task-497) : inchangés.
- L'ancienneté J+N, les seuils et la légende : task-498. La légende y dessinera aussi les deux pastilles.
- Le tableau de bord : task-499.

## Definition of Done

- [ ] Build passes : `nx build weda2`, client-mobile (0 erreur) ; api-mail inchangé hors catalogue.
- [ ] Tests pass : `nx test mss-lib`, `nx test weda2`, client-mobile (0 échec).
- [ ] Tests de composant de la ligne, weda2 et mobile, chacun vu rouge :
      - plus de « Non affecté » sur la ligne, toujours dans l'état en clair ;
      - plus d'identifiant écrit sur la ligne (weda2), présent dans l'infobulle de l'anneau, absent du libellé
        accessible ; sans anneau, dans l'infobulle de l'initiale ;
      - pastille du compteur sur l'anneau d'un fil de 2 messages, « 99+ » au-delà de 99, aucune pastille hors vue
        conversation ou pour un message seul ; plus de « N messages » dans la ligne en mode anneau ;
      - mobile : un appui sur la pastille déplie le fil sans ouvrir le message, `aria-expanded` suit ;
      - icône « répondu » au bord de l'anneau ouvert comme fermé, plus dans la ligne ; infobulle = phrase du bandeau ;
      - ligne sans anneau : « N messages » et icône « répondu » à leur place d'aujourd'hui.
- [ ] Tests de composant des allègements complémentaires, chacun vu rouge :
      - 2 valeurs de biologie au plus, critiques d'abord, « +N autres » avec son libellé accessible ; 2 valeurs ou moins :
        aucune mention (weda2 et mobile) ;
      - weda2 : date du document absente sur un message ordinaire et sur un document daté du jour de réception, présente
        sinon ;
      - weda2 : aucun type écrit sur un message sans document médical, « BIOLOGIE » sur un compte rendu de biologie ;
      - weda2 : pas d'« Envoyé » dans Envoyés ni dans un sous-dossier, « Envoyé » en vue conversation et en vue par
        étiquette ; même règle pour « Brouillon » ;
      - mobile : pas de puce « Biologie » en mode anneau, présente en icône classique ; plus de « (H) » ; « Document
        médical v2 » dans l'infobulle et le libellé accessible de l'icône.
- [ ] Test de composant de l'anneau, weda2 et mobile : à 32 px, les pastilles sont hors du cercle des initiales et du
      badge ⚠ (positions relues), vu rouge.
- [ ] Contraste du chiffre blanc sur la pastille gris foncé ≥ 4,5:1 ; couleur par jeton du design system quand il
      existe (weda2 : `--ds-*`).
- [ ] `data-testid` conservés (règle 7) ; nouveaux `data-testid` sur la pastille de réponse si elle change d'élément.
- [ ] Scénario **E2E-RING-003** monté en **version 2** dans `Api/Mail/e2e/scenarios.yml` : « Non affecté » n'est plus
      lu sur la ligne mais dans l'état en clair de l'anneau. Tests des deux clients mis à jour.
- [ ] Scénario **E2E-RING-005** (version 1, `mobile: requis`, `angular: requis`) ajouté au catalogue et implémenté dans
      les deux clients : le test dépose un message à traiter d'objet unique, puis une réponse du même fil. En vue
      conversation, l'anneau du fil porte la pastille « 2 » ; la ligne n'écrit pas « 2 messages » ; un appui sur la
      pastille (mobile) ou sur le chevron (weda2) déplie le fil. Le praticien répond au message : relu du serveur, il
      est répondu, et son anneau porte l'icône « répondu », dont l'infobulle est la phrase du bandeau.
- [ ] Mobile : référence Stitch de l'écran `mail-list` mise à jour (`/stitch-design`, best-effort).
- [ ] `python Tools/contracts/contract_impact.py check` : aucun impact (aucun contrat ne change).

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil de développement habituel).
- weda2 : `cd Client/Angular/front && npm run start:weda2`. Mobile : `cd Client/Mobile && npm start`.
- Données : une boîte partagée avec un délégataire ; un message à traiter non attribué ; une conversation de 3 messages
  dont un à traiter ; un message auquel on a répondu, encore à traiter ; un autre répondu et traité.
- Référence visuelle : `Docs/specs/anneau-de-traitement/maquettes.html`, variante D, section 2 (liste).

1. weda2, Boîte de réception, vue liste : aucune ligne n'écrit « Non affecté » ni `[1234]`. Au survol de l'anneau du
   message non attribué, l'infobulle dit « … Non affecté. — Identifiant : … ».
2. Le message répondu encore à traiter : anneau ouvert, icône « répondu » à son bord, infobulle « Vous avez répondu à
   ce message le … ». Le message répondu et traité : coche, et la même icône au bord.
3. Passer en vue conversation : l'anneau du fil porte une pastille grise « 3 » ; la ligne n'écrit plus « 3 messages » ;
   le chevron déplie le fil.
4. Corbeille : les lignes gardent l'initiale ; l'infobulle de l'initiale donne l'identifiant.
5. Réglages, « Icône classique » : la ligne est celle d'avant l'anneau (« N messages », icône « répondu » dans la ligne),
   sans identifiant écrit.
6. Mobile, mêmes données : points 1 à 3 (sans identifiant) ; en vue conversation, un appui sur la pastille déplie le fil
   sans ouvrir le message ; un second appui le replie.
7. Données complémentaires : un bilan de biologie à 5 valeurs anormales dont 1 critique ; un compte rendu daté de la
   veille de sa réception ; un message ordinaire. weda2 : le bilan montre la valeur critique, une autre, puis « +3 autres » ;
   le compte rendu montre sa date de document, le message ordinaire une seule date et aucun « MESSAGE ». Dossier Envoyés :
   aucune ligne n'écrit « Envoyé » ; en vue conversation, la réponse envoyée l'écrit.
8. Mobile : le bilan n'a pas de puce « Biologie » (mode anneau), ses valeurs n'ont pas de « (H) », et le document médical
   est une icône dont l'appui long dit « Document médical ». En icône classique, la puce « Biologie » revient.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du cabinet).
- **Vague Ségur** : hors Ségur — ergonomie de la liste, aucune exigence DSR nouvelle.
- **Exigences DSR honorées** : non applicable.
- **INS** : non applicable — aucun patient identifié ni manipulé.
- **Authentification PS** : inchangée — session PSC (e-CPS) de la messagerie.
- **Habilitations** : inchangées — la ligne affiche ce que la personne voit déjà.
- **Interop CI-SIS** : non applicable.
- **Tracé PGSSI-S** : aucun acte nouveau (affichage seul).
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : inchangé — aucune donnée nouvelle, aucune donnée de santé dans les infobulles (l'identifiant
  IMAP est technique).
- **AIPD / impact RGPD** : inchangée.
