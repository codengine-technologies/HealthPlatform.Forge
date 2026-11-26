# todo-task-495 — « Pour le compte de » visible dans la conversation et dans l'aperçu

**Repos**: dtos-mss, api-mail, client-mobile, client-angular
**Dependencies**: aucune (task-407, qui pose et lit le `Sender`, est archivée)
**Epic**: E020

> **Cadre** : *MSSanté – Guide d'implémentation de la délégation de BAL via API LPS*, ANS, **v1.0 du
> 26/11/2026** (`Docs/Referentiel/MSSANTE/MSSanté - Guide d'implémentation de la délégation de BAL v1.0.pdf`),
> §3.3, exigence **ECO.1.2.10** : « Si le message reçu contient un champ Sender alors le système DOIT afficher à
> l'utilisateur dans l'entête du message reçu que l'« Expéditeur » du message est le délégataire et qu'il l'a
> envoyé pour le compte du délégant. »
>
> **Origine** : audit de conformité du 2026-11-26 contre ce guide (écarts 2 et 3). task-407 a couvert ECO.1.2.10
> dans l'**écran de lecture** d'un message (mobile et weda2). Deux autres vues montrent un message reçu, et
> n'affichent que la boîte : le lecteur y attribue au titulaire un message écrit par son délégataire.

## Ce qui est établi

- **Écran de lecture, conforme** (task-407) : mobile `mail-detail.component.ts:741-754` et weda2
  `libs/mss/.../mail-detail.component.ts:587-600` affichent « Envoyé par {Sender} pour le compte de {From} »,
  seulement si le `Sender` est présent et différent du `From`. Scénario E2E-SHARED-002.
- **Vue conversation, écart** :
  - le serveur ne renseigne l'auteur que pour les messages **envoyés** par la boîte :
    `ConversationService.cs:283`, `Author = bubble.IsSent ? MailReplySummaries.AuthorOf(…) : null` ;
  - `ConversationMessageDto` (`Dtos/MailConversationDto.cs:55-90`) porte `From` et `Author`, pas de `Sender` ;
  - mobile `conversation-chat.page.ts:879` (`senderNameOf`) et weda2 `chat-bubble.utils.ts:133-142` n'affichent que
    le `From` d'une bulle reçue.
- **Aperçu en lecture seule de weda2, écart** : `mail-read-only-view.component.html:15-16` affiche « De » depuis
  `mail.from` seul. Il sert dans la fiche patient (`patient-widget.component.html:144`) et dans le dialogue de
  nettoyage des doublons. Le `MailDto` qu'il reçoit porte déjà le `Sender`.
- **Mobile n'a pas d'aperçu en lecture seule** : aucun composant équivalent dans `Client/Mobile/src`.
- **Réponse depuis la conversation, conforme** (ECO.1.2.11) : les destinataires sont calculés côté serveur depuis
  `From`, `To`, `Cc` (`ConversationParticipants.cs:10-14, 99-110`), jamais depuis le `Sender`.
- **Le `Sender` lu à l'ingestion** est déjà nettoyé : absent, ou égal au `From`, il est vide
  (`EmailAddressHelper.ExtractSenderAddress`). Il est persisté (`Mails.SenderName`, `Mails.SenderAddress`).

## Objective

Un médecin qui lit un message écrit par un délégataire pour le compte d'une boîte le sait, quelle que soit la vue
où il le lit : écran de lecture (déjà fait), **conversation** (mobile et weda2), **aperçu** de weda2 (fiche
patient, doublons).

## Règles

1. **Bulle reçue dans la conversation** : quand le message porte un `Sender` différent du `From`, la bulle garde
   le nom de la boîte (`From`) et affiche, sous ce nom, « Envoyé par {nom du Sender} pour le compte de {nom du
   From} ». C'est **le même libellé** que l'écran de lecture. Sans `Sender`, aucune mention.
2. **Bulles envoyées** : inchangées. Elles portent déjà l'auteur réel (task-407, règle 14).
3. **Aperçu en lecture seule de weda2** : la même mention, sous la ligne « De ».
4. **Le serveur décide** : le message de conversation porte le `Sender` (nom, adresse) **seulement** s'il est
   présent et différent du `From`, comme `MailDto`. Le client n'analyse aucun en-tête.
5. **Répondre depuis la conversation (ECO.1.2.11)** : comportement inchangé. La réponse et la réponse à tous ne
   visent jamais l'adresse du `Sender`, et un test le verrouille.
6. **Règle 14** : aucun acte nouveau. L'ouverture d'une conversation est déjà tracée au nom de la personne réelle,
   et rien ne change dans ce qui appartient à la boîte ou à la personne.
7. **Rien d'autre ne change** : liste des messages (elle garde le `From`), écran de lecture, envoi.

## Definition of Done

- [ ] Build passes (0 errors) sur `dtos-mss`, `api-mail`, `client-mobile`, `client-angular` (code-only)
- [ ] Tests pass (0 failures) sur chaque repo listé
- [ ] Contrat `dtos-mss` : le `Sender` (nom, adresse) sur le message de conversation (`ConversationMessageDto`),
      package publié, consommateurs .NET bumpés, types TypeScript mobile et weda2 mis à jour
- [ ] Unit tests de la construction du message de conversation : message reçu avec `Sender` → renseigné ; sans
      `Sender` → vide ; message envoyé → inchangé (`Author` toujours calculé)
- [ ] Test d'intégration de bout en bout pour `GET` de la conversation : un message **reçu** dont l'en-tête
      `Sender` diffère du `From` porte ce `Sender` (nom et adresse) dans la réponse réelle ; un message reçu sans
      `Sender` le porte vide — vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout : la réponse depuis la conversation à un message porteur d'un `Sender`
      part vers le `From` ; l'adresse du `Sender` n'est dans aucun destinataire du message reçu — vu rouge
      (règle 1b)
- [ ] Mobile et weda2 : la bulle reçue affiche la mention ; `data-testid` sur la mention
- [ ] weda2 : l'aperçu en lecture seule affiche la mention ; `data-testid` sur la mention
- [ ] UI component tests : bulle mobile, bulle weda2, aperçu weda2 — mention présente avec un `Sender`, absente
      sans `Sender` et quand il est égal au `From`
- [ ] Scénario E2E-SHARED-003 (v1 : dans la conversation, la bulle d'un message reçu écrit par le délégataire
      affiche « Envoyé par {délégataire} pour le compte de {boîte} » ; une bulle sans `Sender` n'affiche rien ;
      « Répondre » vise la boîte) ajouté dans Api/Mail/e2e/scenarios.yml, et implémenté dans chaque client où il
      est requis — `clients` : mobile requis, angular requis
- [ ] Scénario E2E-SHARED-004 (v1 : dans la fiche patient, l'aperçu d'un message rattaché écrit par le délégataire
      affiche la mention) ajouté dans Api/Mail/e2e/scenarios.yml, et implémenté dans chaque client où il est
      requis — `clients` : angular requis, mobile non-applicable — l'aperçu en lecture seule d'un message n'existe
      pas dans l'application mobile
- [ ] Aucune donnée de santé en clair dans les logs (INS, NIR, contenu CDA, contenu MSSanté) ; aucun RPPS affiché
      ni dans un en-tête
- [ ] `client-angular` : fichiers à commiter sur TFS listés dans le `## Develop log`, avec la raison de chacun

## Manual Test Plan

- Backend e2e : `cd Api/Mail && dotnet run --project src/AppHost` (profil `e2e`) ; mobile
  `cd Client/Mobile && npm start` ; weda2 via le faux hôte.
- Données : titulaire e2e et délégataire e2e sur `boite-praticien` (seed `delegataire`, task-404).
- Le délégataire, depuis `boite-praticien`, écrit un message à `boite-praticien` elle-même (comme E2E-SHARED-002).
- Côté titulaire, ouvrir la **conversation** de ce message (mobile, puis weda2) : la bulle reçue affiche
  « Envoyé par {Prénom Nom du délégataire} pour le compte de {nom de la boîte} ».
- Ouvrir la conversation d'un message reçu ordinaire (`mail-lu`) : aucune mention.
- Répondre depuis la conversation : la réponse vise la boîte, jamais l'adresse `no-reply-…` du délégataire.
- weda2 : rattacher le message du délégataire à un patient, ouvrir la fiche patient et son aperçu : la mention
  s'affiche sous « De ».

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — exigence du guide ANS de délégation de BAL, non encore intégré aux référentiels
  (le guide annonce son intégration dans les prochaines versions du référentiel clients)
- **Exigences DSR honorées** : guide ANS de délégation de BAL v1.0 (26/11/2026), **ECO.1.2.10** (et ECO.1.2.11
  verrouillé par test)
- **INS** : non applicable — la mention ne manipule aucune donnée patient ; l'aperçu de la fiche patient reste
  inchangé hors de la ligne « De »
- **Authentification PS** : PSC / e-CPS, inchangée
- **Habilitations** : inchangées ; un délégataire ou un membre ne voit la conversation et la fiche qu'avec un
  verdict récent de l'opérateur (task-403)
- **Interop CI-SIS** : non applicable ; en-têtes MSSanté RFC 5322 (`From`, `Sender`) déjà lus à l'ingestion
- **MSSanté** : BAL personnelle ou organisationnelle déléguée ; `Sender` posé par le logiciel du délégataire
  (le nôtre depuis task-407, ou un autre LPS conforme)
- **Tracé PGSSI-S** : aucun évènement nouveau ; ouverture de conversation et consultation de fiche déjà tracées,
  imputées à la personne réelle. Conservation inchangée (3 653 jours pour `HealthDataAccess`)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé
- **AIPD / impact RGPD** : inchangé — le nom du délégataire est déjà communiqué au destinataire dans l'en-tête
  du message et affiché dans l'écran de lecture (task-407) ; il l'est dans deux vues de plus, sans nouveau
  traitement

## Branches

- `dtos-mss` (branche paresseuse) : créée par `/develop` au moment où il touche le contrat (`ConversationMessageDto.Sender`)
- `api-mail` (pushed) : feat/task-495-pour-le-compte-de-conversation-et-apercu — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-495-pour-le-compte-de-conversation-et-apercu
- `client-mobile` (pushed) : feat/task-495-pour-le-compte-de-conversation-et-apercu — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/feat/task-495-pour-le-compte-de-conversation-et-apercu
- `client-angular` (code-only) : branche checkout au /start : `feature/nova-mss-weda-integration` — humain gère branche, commit, push, PR TFS

## Timings

*(généré par `tools/timing/report.sh --task task-495 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 32 s | — | — | — | — |
| /develop | ok | 45 min 29 s | 6 (1 min 10 s) | 14 (12 min 17 s) | — | dtos-mss 1B/0T, api-mail 1B/8T, client-angular 2B/4T, client-mobile 2B/2T |
| /review-code | ok | 2 min 57 s | — | — | — | — |
| **Total cycle** | | **48 min 59 s** | **6 (1 min 10 s)** | **14 (12 min 17 s)** | **0 (0.0 s)** | |

Autres commandes mesurées : nuget-wait ×1 (23 s), restore ×1 (3.8 s)

## Develop log

- Repos touched : dtos-mss, api-mail, client-mobile, client-angular (code-only). `client-blazor` non listé : son paquet
  dtos-mss reste en 533.0.0 (écart 1 de l'audit, hors périmètre).
- DTOs published : `HealthPlatform.Dtos.Mss` 632.0.0 → **635.0.0** (`ConversationMessageDto.Sender`, run CI 635 vert).
- Interop published : no interop change.
- **Identifiants de scénarios — écart avec la DoD** : E2E-SHARED-003 existait déjà au catalogue (task-492, « traité
  par »). Les deux scénarios de la task sont donc **E2E-SHARED-004** (conversation, la DoD dit « 003 ») et
  **E2E-SHARED-005** (aperçu de la fiche patient, la DoD dit « 004 »). Contenu et colonne `clients` conformes à la DoD.
- Commits :
  - dtos-mss : `03f16e1` feat(dto): Sender d'un message reçu dans la conversation
  - api-mail : `a5650e41` chore(deps): bump Dtos.Mss 635.0.0 ; `4267bff2` feat(conversation): Sender d'un message
    reçu (+ catalogue, outil e2e `--sender`) ; `ec5cc612` test(e2e): E2E-SHARED-005 dans sa forme finale
  - client-mobile : `11e6c64` feat(mobile): mention sous la bulle reçue ; `70c161b` refactor(mobile): simplify pass
- Comportement : `ConversationService` rend `Sender` (nom, adresse) pour un message **reçu** dont l'en-tête Sender a été
  gardé à l'ingestion (jamais égal au From) ; un message envoyé garde son auteur dans `Author`. Règle d'affichage
  unique par client : `core/utils/on-behalf-of.util.ts` (mobile et weda2), reprise par l'écran de lecture, la bulle de
  conversation et (weda2) l'aperçu en lecture seule.
- Preuves rouges (règle 1b et e2e) :
  - **Intégration** `ConversationEndToEndTests.AReceivedMessageWrittenOnBehalf_NamesItsSender_AndTheReplyGoesToTheFrom`
    (Dovecot, PostgreSQL, GreenMail réels) : mutation M1 `Sender = null` → rouge ligne 354 (Expected
    `(no-reply-cyril.delegue@…, Cyril DELEGUE)`, Actual `(null, null)`) ; mutation M2 « le Sender entre dans les
    adresses du fil » → rouge ligne 359 (ReplyRecipients `[moreau, no-reply-…]`). Restaurés depuis copie, diff relu.
  - **Unitaire** `ConversationServiceTests.Get_AReceivedMessageWrittenOnBehalf_CarriesItsSender_ASentOneNever` vu rouge
    avant le code ; `Reply_ToAMessageWrittenOnBehalf_GoesToTheFrom_NeverToTheSender` vert d'emblée (comportement
    ECO.1.2.11 déjà conforme, verrouillé, et vu rouge par M2 côté intégration).
  - **Composants** : mobile `conversation-chat.page.spec` (mutation `onBehalfOf: null` → « Expected $.length = 0 to
    equal 1 ») ; weda2 `mail-conversation.component.spec` et `mail-read-only-view.component.spec` (mutations bulle et
    aperçu → 2 rouges sur les assertions prévues). Lancés via PowerShell (mémoire vitest-mss-lanceur-instable).
  - **e2e mobile** E2E-SHARED-004 (`--serve-only` + `--grep`) : vert 5,6 s ; mutation servie (bundles 1 → 2, marqueur
    1) → rouge « la bulle dit qui a écrit, pour qui » ; restauré, bundle 3, vert 3,8 s.
  - **e2e weda2** E2E-SHARED-004 et 005 : verts ; mutations bulle et aperçu prouvées **servies** (marqueurs trouvés
    dans les chunks de https://localhost:4200) → 2 rouges sur « la bulle dit… » et « l'aperçu dit… » ; restaurées
    (marqueurs absents), 2 verts.
- Local build / test :
  - api-mail : build 0 erreur ; suite complète 0 échec (domain 368, infrastructure 749, application 4 362, api 1 388,
    intégration 1 376 + 16 ignorés), sans crash ni total tronqué. `ScenarioCatalogTests` 17/17 après chaque
    modification du catalogue.
  - client-mobile : `npm run build` vert ; suite 1 718/1 718 (après passe qualité).
  - client-angular : `nx build weda2` vert ; `nx test mss-lib` 1 955/1 955 (après passe qualité) ; `nx test weda2`
    2 683/2 683.
  - `tsc` des deux suites e2e et ESLint des fichiers touchés : 0 erreur (aucun avertissement dans les lignes ajoutées).
- Contrat des consommateurs (Step 4c) : `contract_impact.py check` → api-mcp, client-mobile, client-angular **aucun
  impact** (ajout de champ ; avertissements de lecture tolérante préexistants).
- Passe qualité (/simplify) :
  - Applied & committed : client-mobile : 4 fichiers (`70c161b`) — `addressLabel`/`normalizeAddress` réutilisés, style
    `.chat-sender` réutilisé, conversation e2e lue une fois dans son attente, deux attentes d'UID en parallèle.
  - Applied (code-only, uncommitted) : client-angular : `on-behalf-of.util.ts` (mêmes réutilisations), test e2e
    E2E-SHARED-004 (conversation lue dans son attente).
  - No change : api-mail — un constat noté, non appliqué : `SenderOf` recopie la projection `Sender` de
    `MailRepository` (×3), convention `projection-dto-dupliquee` ; l'unification touche `MailRepository`, hors diff.
  - Skipped (contract) : dtos-mss.
  - Écartés : assertion négative e2e « aucune mention sans Sender » (gardée : lisible, gratuite), cas m-3 du spec de
    page (passe par le parent, convention tester-a-travers-le-parent).
- Prévention (règle d'or) : `conventions/csharp.md` S125 → 40 (×3 « … ; … » attrapés avant commit) ;
  `conventions/e2e.md` : `stop-du-banc-laisse-en-place`, `widget-patients-non-lus-trois-conditions`.
- Stitch : aucun écran mobile créé ni réécrit (une ligne de texte ajoutée sous le nom d'une bulle existante) ; pas de
  sous-étape `/stitch-design`.
- DOD self-check : 13/14 vérifiables par commande, vérifiés ; reste « fichiers client-angular listés pour TFS » (ci-dessous).
- Green marked : api-mail (`4267bff2`, avant le commit catalogue `ec5cc612` : `/review` rejouera), client-mobile
  (`70c161b`), client-angular (arbre final).
- Next step : /review task-495 --code

### client-angular — fichiers à commiter sur TFS (branche `feature/nova-mss-weda-integration`)

**À commiter avant le merge de la PR api-mail** (conventions/e2e.md, `test-angular-non-commite`) : les scénarios
E2E-SHARED-004 et 005 sont `requis` pour angular.

- `front/libs/mss/src/core/utils/on-behalf-of.util.ts` (nouveau) et `.spec.ts` — la règle de la mention, une seule fois.
- `front/libs/mss/src/core/models/conversation.model.ts` — `sender` du message de conversation (contrat dtos-mss 635).
- `front/libs/mss/src/features/mail/components/mail-conversation/chat-bubble.{model,utils}.ts`, `.component.html`,
  `.component.scss` — la mention sous le nom d'une bulle reçue.
- `front/libs/mss/src/features/mail/components/mail-conversation/mail-conversation.component.spec.ts` — test de la bulle.
- `front/libs/mss/src/features/mail/components/mail-read-only-view/mail-read-only-view.component.{ts,html,scss,spec.ts}`
  — la mention dans l'aperçu (fiche patient, doublons).
- `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.ts` — l'écran de lecture reprend l'utilitaire.
- `front/e2e/mss-e2e/specs/functional.e2e.ts` — E2E-SHARED-004 et E2E-SHARED-005.
- `front/e2e/mss-e2e/support/e2e-backend.ts` — option `sender`, `markUnread`, `lastUnreadMailOf`, type `sender` de la conversation.

## Code Review Summary

### Passage 1 (revue anticipée) — APPROVED

- **approved at** : dtos-mss `03f16e1` · api-mail `ec5cc612` · client-mobile `70c161b` · client-angular : arbre de
  travail de `feature/nova-mss-weda-integration` (base `20363c73`, non commité, code seul).
- Relecteur indépendant (sous-agent, code seul, sans les conclusions de la forge) : **APPROVED**, 0 bloquant.
- **4a — règle 1b** (comportement → test → preuve rouge) :
  | Comportement (route) | Test d'intégration | Preuve rouge |
  |---|---|---|
  | `GET api/v1/mail/conversation/{id}` : un message reçu porte son `Sender` (nom, adresse) ; vide sans Sender ou Sender = From | `ConversationEndToEndTests.AReceivedMessageWrittenOnBehalf_NamesItsSender_AndTheReplyGoesToTheFrom` | mutation M1 `Sender = null` → rouge l. 354 |
  | `GET …/conversation` + `POST …/reply` : `ReplyRecipients` et la réponse délivrée visent le `From`, jamais le `Sender` | même test | mutation M2 (Sender dans les adresses du fil) → rouge l. 359 |
- **4c — consommateurs du contrat** : `api-mcp : aucun impact` · `client-mobile : aucun impact` ·
  `client-angular : aucun impact` (ajout de champ).
- **4b — clause DoD du parcours** : E2E-SHARED-004 v1 (mobile requis, angular requis) et E2E-SHARED-005 v1 (angular
  requis, mobile non applicable, raison fonctionnelle) au catalogue, versions égales à celles des tests. Identifiants
  décalés d'un rang par rapport à la DoD (SHARED-003 déjà pris par task-492), contenu conforme.
- Suggestions (⚠️, non bloquantes, techniques) :
  1. Tests e2e (mobile E2E-SHARED-004, weda2 E2E-SHARED-004 et 005) : les messages sont déposés avant le `try` ; un
     échec du second dépôt laisserait le premier (porteur d'un Sender) dans `boite-praticien`. Déplacer les dépôts
     dans le `try` (les suppressions du `finally` tolèrent un message absent).
  2. weda2 E2E-SHARED-004 : `const [first, second] = thread?.messages` suppose l'ordre du serveur ; choisir par uid
     comme le test mobile (sans risque de vert menteur : `newText` est affirmé aussitôt).
