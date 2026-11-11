# todo-task-446.md — Recherche : lire un résultat (extrait surligné, patients trouvés)

**Repos**: client-angular, api-mail
**Dependencies**: done-task-444 (réponse enrichie), done-task-445 (mode résultats)
**Epic**: E023
**Priorité**: EPIC E023, demandée par l'humain le 2026-11-10. Le médecin doit reconnaître le bon message sans l'ouvrir,
et passer d'un nom tapé au dossier du patient en un geste.

> **Origine.** Analyse du 2026-11-10 (surlignage et « Personnes » d'Outlook). `api-mail` figure dans les Repos pour le
> catalogue e2e.

## Objective

Dans le mode « Résultats de recherche » de weda2, chaque résultat explique pourquoi il est là, et les patients désignés
par la recherche sont proposés en tête.

Règles :
- **Extrait surligné** : sous l'objet de chaque résultat, l'extrait rendu par le serveur, avec les termes trouvés
  surlignés.
- **Endroit trouvé** : une mention courte indique où le terme a été trouvé (« Objet », « Corps », « Document médical »,
  « Expéditeur », « Pièce jointe »), ou « Proche par le sens » pour un résultat proche.
- **Dossier d'origine** : chaque résultat porte le nom du dossier où il est rangé (« Boîte de réception »,
  « Archives »…).
- **Patients trouvés** : au-dessus des résultats, une rangée « Patients » montre au plus 5 patients désignés par la
  recherche (nom de naissance en majuscules, nom d'utilisation s'il diffère, prénom, date de naissance, sexe, nombre de
  messages, mention « INS qualifiée » le cas échéant). Un clic ouvre la vue existante « Mails du patient ».
  - L'INS n'est jamais affichée.
  - Aucun patient trouvé : la rangée n'est pas affichée.
- Le surlignage est aussi appliqué dans le message ouvert depuis les résultats (objet et corps).

### Hors périmètre

- Le mobile : task-451.
- Les patients proposés pendant la frappe : task-449.

## Definition of Done

- [ ] Build passes (0 errors) : weda2 (`nx build weda2`)
- [ ] Tests pass (0 failures) : `nx test weda2`, `nx test mss-lib`
- [ ] Tests de composant, chacun vu rouge par mutation : extrait surligné aux positions rendues (y compris un mot
      accentué tapé sans accent) ; mention de l'endroit trouvé ; dossier d'origine ; rangée Patients (affichée, masquée
      sans patient, clic vers « Mails du patient ») ; aucune INS dans le rendu ; surlignage dans le message ouvert
- [ ] Le surlignage est rendu sans injection : un extrait contenant du balisage s'affiche comme du texte (test dédié)
- [ ] **Scénario e2e** `E2E-SEARCH-010` v1 ajouté à `Api/Mail/e2e/scenarios.yml` : « Reconnaître un résultat et ouvrir
      le dossier du patient » — attendu : l'extrait surligne le terme cherché, et le patient désigné ouvre ses messages.
      Clients : angular requis, mobile requis avec **divergence temporaire** (raison : « la lecture enrichie arrive sur
      le mobile avec la refonte mobile », tache : task-451). Implémenté dans weda2, vu rouge par mutation
- [ ] `data-testid` sur chaque élément interactif ajouté (rangée Patients, chaque patient)
- [ ] Aucune chaîne en dur hors des conventions de libellés
- [ ] client-angular : code-only, aucun commit
- [ ] **Prévention (règle d'or)** : consigne dans `conventions/angular.md` : un surlignage se construit à partir de
      positions et de texte échappé, jamais en injectant du HTML reçu

## Manual Test Plan

1. Lancer le backend sur le corpus fictif de task-438 : `cd Api/Mail/src/AppHost && dotnet run`, puis le seed de
   référence. Lancer weda2 : `cd Client/Angular/front && npm start`.
2. Rechercher `hemoglobine` : chaque résultat montre un extrait où « hémoglobine » est surligné, la mention « Document
   médical » ou « Corps », et son dossier d'origine.
3. Rechercher `bernard catherine` : la rangée « Patients » montre Catherine BERNARD, sa date de naissance et son nombre
   de messages, sans INS. Cliquer : la vue « Mails du patient » s'ouvre.
4. Rechercher `bernart` : aucune rangée Patients.
5. Ouvrir un résultat : les termes sont surlignés dans l'objet et le corps.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — ergonomie de la recherche
- **Exigences DSR honorées** : non applicable
- **INS** : jamais affichée ; seul le statut « INS qualifiée » est montré, pour que le médecin sache s'il peut se fier à
  l'identité. Les traits affichés sont ceux de l'identito-vigilance (nom de naissance, prénom, date de naissance, sexe)
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : inchangées — verdict de l'opérateur MSSanté (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé — la recherche est tracée côté serveur (`MailSearch`) ; l'ouverture de la vue « Mails du
  patient » est tracée comme aujourd'hui, au nom de la personne réelle, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable au client — aucune donnée stockée
- **AIPD / impact RGPD** : couvert par task-444 (affichage d'extraits)

## Branches

- `api-mail` (pushed) : feat/task-446-recherche-lire-un-resultat-extrait — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/feat/task-446-recherche-lire-un-resultat-extrait
- `client-angular` (code-only) : la forge écrit sur la branche checked out dans `Client/Angular/` (au /start : `feature/nova-mss-weda-integration`) — humain gère branche, commit, push, PR TFS

## Develop log

- Repos touched : `api-mail` (catalogue e2e), `client-angular` (code-only, non commité)
- DTOs published : no DTO change (contrat de task-444 : `locations`, `excerpt`, `excerptLocation`, `highlights`,
  `patients`, `isPatientsTruncated`)
- Interop published : no interop change
- Commits :
  - api-mail : `783ff7e1` test(e2e): task-446 — scénario E2E-SEARCH-010
  - client-angular : **aucun commit** — sur `feature/nova-mss-weda-integration` (l'arbre porte encore le travail non
    commité de task-442/443/445) :
    - nouveaux : `libs/mss/src/core/utils/text-highlight.util.ts` (+ spec),
      `components/mail-detail/mail-detail.search-highlight.spec.ts`
    - modifiés : `core/models/search.model.ts`, `services/mail-search-session.ts`,
      `components/mail-search-results/` (ts, html, scss), `components/mail-detail/` (ts, html, scss, 5 specs : double
      de `MailStateService` complété de `search`), `components/mail-body/` (ts, html, scss, spec),
      `components/mail-list/mail-list.search-mode.spec.ts`, `e2e/mss-e2e/specs/functional.e2e.ts`
- Conception :
  - `text-highlight.util.ts` : `highlightSegments` (positions → segments, bornées, fusionnées ; le texte rendu est le
    texte d'origine), `findTermRanges` (repli accents + casse, positions d'origine), `searchTermsOf`, `highlightHtml`
    (nœuds de texte d'un document inerte, hors `script`/`style`, `<mark>` créés par le DOM). Jamais de HTML reçu injecté.
  - Résultats : sous chaque ligne, le dossier d'origine (« Boîte de réception » pour la boîte de réception), l'endroit
    trouvé (« Objet · Corps », « Document médical », « Expéditeur », « Pièce jointe », « Proche par le sens ») et
    l'extrait surligné aux **positions du serveur**. Rangée « Patients » en tête (5 au plus, rendus par le serveur) :
    `NOM Prénom, née le …`, sexe, nombre de messages, « INS qualifiée » ; un clic ouvre `/messagerie/mail?patient=…`
    (vue « Mails du patient » existante). Aucune INS : le contrat n'en porte pas, et un champ glissé n'est pas rendu.
  - Message ouvert pendant une recherche : objet (`mail-detail`) et corps texte / HTML (`mail-body`, mémoïsé) surlignés
    sur les mots de la recherche affichée, sans accent ni casse.
- Limite assumée : « nom d'utilisation s'il diffère » non affiché — le serveur ne garde qu'un nom par patient (reste
  connu de task-444).
- Local build / test :
  - api-mail : build 0 erreur ; `dotnet test` 7 788 verts (intégration 1 250 + 16 ignorés), 0 échec.
  - client-angular : `nx test mss-lib` 1 599 verts (142 fichiers) ; `nx test weda2` 2 683 ; `nx build weda2` vert
    (avertissements NG8107 préexistants) ; `tsc -p e2e/mss-e2e/tsconfig.json` vert ; ESLint ciblé 0 erreur (`max-lines`
    préexistants seulement).
- Preuve par mutation — tests de composant (Vitest, rouges sur le test prévu, puis restaurés) :
  N1 extrait sans surlignage → 1 ; N2 accents non repliés → 7 ; N3 endroit non dit → 1 ; N4 dossier par son chemin → 1 ;
  N5 rangée Patients jamais affichée → 2 ; N5b toujours affichée → 2 ; N5c clic sans navigation → 1 (premier essai
  invalide : la mutation ne compilait pas, rejouée) ; N6 INS rendue → 1 ; N7 extrait en `[innerHTML]` → 2 ; N8 objet
  non surligné → 1 ; N8b mots non transmis → 2 ; N9 texte brut non surligné → 1 ; N10 corps HTML non surligné → 1 ;
  N11 `style` marqué → 1.
- Preuve par mutation — parcours e2e (banc `--serve-only`, marqueur relu dans le bundle servi, retiré après) :
  F1 extrait sans surlignage → E2E-SEARCH-010 rouge (aucun `mark`) ; F2 endroit absent → rouge (« Corps ») ; F3 rangée
  Patients vide → rouge (0 patient) ; F4 clic sans navigation → rouge (URL sans `?patient=`). Témoin restauré :
  E2E-SEARCH-001 à 010, 10/10 verts.
- Passe qualité (/simplify) : client-angular — aucune simplification appliquée (`mailKeyString`, segments et mémo
  déjà factorisés) ; api-mail — catalogue seul ; skipped : dtos-mss, interop-cda.
- Prévention (règle d'or) : `conventions/angular.md` « surlignage-par-positions ».
- DOD self-check : 9/9 commandables vérifiés (build, tests, tests de composant rouges sous mutation, test
  anti-injection, E2E-SEARCH-010 au catalogue avec divergence mobile task-451 et implémenté dans weda2, rouge sous
  mutation, `data-testid` sur la rangée Patients et chaque patient, libellés en dur, Angular non commité, consigne).
  Manual Test Plan : HAG.
- ⚠️ À commiter sur TFS **avant** le merge de la PR api-mail : `functional.e2e.ts` (E2E-SEARCH-010, et 004 à 009 de
  task-445 s'ils ne le sont pas déjà).
- Next step : /sonar task-446

## Sonar log

- Mode A (chaîné), branche `feat/task-446-recherche-lire-un-resultat-extrait`, commit analysé `783ff7e1` (diff api-mail :
  `e2e/scenarios.yml` seul, aucun code analysé).
- Analyse complète : Release, 5 passes OpenCover (0 échec), `ANALYSIS SUCCESSFUL`, traitement serveur `SUCCESS`.
- Itérations : 0.

| KPI | Baseline | Final |
|---|---|---|
| Quality Gate | OK | **OK** |
| Bugs / Vulnerabilities / Hotspots | 0 / 0 / 0 | 0 / 0 / 0 |
| Code Smells | 0 | 0 |
| Coverage | 97,8 % | 97,8 % |
| Duplication | 0,4 % | 0,4 % |
| Reliability / Security / Maintainability | A / A / A | A / A / A |
| New code — issues | — | 0 |
| New code — coverage | — | 96,2 % |

- Conventions : aucune règle corrigée → `conventions/csharp.md` inchangé.

## Lint log

- client-angular (code-only, `feature/nova-mss-weda-integration`, aucun git) : `npx nx run-many -t lint
  --projects=mss-lib,mss-e2e` (contournement task-367).
- **0 erreur** ; avertissements 52 (`mss-lib`) + 48 (`mss-e2e`), identiques à la base de task-445 : aucun introduit
  (les seuls signalés sur les fichiers touchés sont des `max-lines` préexistants).
- Itérations : 0. Build et tests déjà verts sur l'arbre final (fin de `/develop`).

## Lint mobile log

- skipped — `client-mobile` absent des `**Repos**` et arbre propre.

## E2E log

Rejoué après la 2ᵉ reprise (A1).

| Voie | Jouée / réutilisée | Résultat | Dépôts couverts |
|---|---|---|---|
| mobile | réutilisée (même empreinte que le passage vert de ce cycle) | 60 verts, parité verte | api-mail `783ff7e1`, client-mobile `develop` |
| angular | jouée | 80 verts, 0 flaky, 0 rouge, parité de la colonne verte | api-mail `783ff7e1`, client-angular (arbre corrigé, non commité), Client/Mobile/e2e |

Démontage vérifié : ports libres, aucun conteneur e2e résiduel.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Passed — correction : task-350

### Matrice de parité

| Scénario | v | Mode | Titre | angular | mobile |
|---|---|---|---|---|---|
| E2E-INBOX-001 | 1 | headless | Filtrer la boîte de réception, basculer liste / conversation, ouvrir la recherche | ✅ | ✅ |
| E2E-FOLDER-001 | 1 | headless | Naviguer vers les dossiers Archive et Corbeille | ✅ | ✅ |
| E2E-PATIENT-001 | 1 | headless | Afficher la vue patients | ✅ | ✅ |
| E2E-PATIENT-002 | 2 | headless | Rattacher à la main un document sans INS à un patient choisi par recherche, puis le détacher | ✅ | ✅ |
| E2E-PATIENT-003 | 1 | headless | La fiche d'un patient ne montre pas les documents d'un autre patient du même mail | ✅ | ✅ |
| E2E-PATIENT-004 | 1 | headless | La vue « Mails du patient » reste ouverte et ses pages viennent du serveur | ✅ | — |
| E2E-CONTACT-001 | 2 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 3 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-COMPOSE-004 | 1 | headless | Écrire à l'adresse choisie d'un contact à plusieurs adresses, ou à son adresse par défaut | ✅ | ✅ |
| E2E-COMPOSE-005 | 1 | headless | Une remise incertaine n'est jamais présentée comme un échec à renvoyer | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-MAIL-006 | 1 | headless | Glisser sur la Corbeille un message d'un fil supprime ce message, et lui seul | ✅ | — |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-DRAFT-003 | 1 | headless | Quitter une rédaction récente ne perd rien | ✅ | ✅ |
| E2E-DRAFT-004 | 1 | headless | Une rédaction sans texte dans le corps ne laisse ni brouillon ni question | ✅ | ✅ |
| E2E-BIO-001 | 2 | headless | Acquitter un compte rendu de biologie, à son nom | ✅ | ✅ |
| E2E-BIO-002 | 1 | headless | La puce « Bio à acquitter » montre tous les résultats en attente, sur toutes les pages | ✅ | ✅ |
| E2E-BIO-003 | 1 | headless | Lire un résultat HPRIM puis l'acquitter | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-DETAIL-005 | 1 | headless | Passer rapidement d'un mail à l'autre n'affiche jamais le contenu du précédent | ✅ | ✅ |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SETTINGS-003 | 1 | headless | Lire la version du serveur de messagerie dans les Paramètres | ✅ | ✅ |
| E2E-SETTINGS-004 | 1 | headless | Paramètres indisponibles : rien n'est écrasé | ✅ | — |
| E2E-SEARCH-001 | 2 | headless | Composer ses critères puis lancer la recherche | ✅ | ✅ (v1) · divergence (task-450) |
| E2E-SEARCH-002 | 1 | headless | Un mot rare et accentué trouve le message qui le contient | ✅ | ✅ |
| E2E-SEARCH-003 | 1 | headless | Un numéro de dossier trouve son message, et un seul | ✅ | ✅ |
| E2E-SEARCH-004 | 1 | headless | Un nom de patient tapé sans accent ni majuscule trouve ses messages, puis les messages partiels | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-005 | 1 | headless | Un mot absent de la boîte affiche « Aucun résultat » | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-006 | 1 | headless | Plus de résultats qu'une page — « Voir plus » affiche la suite, jusqu'au dernier | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-007 | 1 | headless | Une recherche en échec affiche un message, et l'ancienne liste n'est plus affichée | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-009 | 1 | headless | Fermer la recherche rend le dossier à la même position ; retirer une étiquette relance sans elle | ✅ | ⛔ non joué · divergence (task-450) |
| E2E-SEARCH-010 | 1 | headless | Reconnaître un résultat et ouvrir le dossier du patient | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-SEARCH-008 | 1 | headless | Restreindre la recherche à un patient et à ses biologies anormales | ✅ | ⛔ non joué · divergence (task-451) |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 2 | headless | Créer un contact à deux adresses, le modifier sans les perdre, puis le supprimer | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-CONTACT-004 | 1 | headless | Consulter un contact depuis le carnet et lui écrire | ✅ | ✅ |
| E2E-CONTACT-005 | 1 | headless | Une fiche modifiée ne se perd pas sans confirmation, une adresse mal formée est refusée | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 2 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 2 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 2 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |
| E2E-MAILBOX-001 | 1 | headless | Changer de messagerie depuis l'écran mail | ✅ | ✅ |
| E2E-MAILBOX-002 | 1 | headless | api-mail indisponible à l'entrée — écran de panne puis réessai | ✅ | ✅ |
| E2E-MAILBOX-003 | 2 | headless | Rattacher ses boîtes depuis « Mes boîtes » en un geste — titulaire et membre | ✅ | ✅ |
| E2E-MAILBOX-006 | 1 | headless | Après le rattachement, l'identité d'expéditeur et la signature sont déjà là | ✅ | ✅ |
| E2E-MAILBOX-004 | 1 | headless | Ajouter une BAL déléguée par saisie — et refus de sa propre adresse | ✅ | ✅ |
| E2E-MAILBOX-005 | 1 | headless | Le délégataire refusé par l'opérateur perd l'accès, en ligne puis hors ligne ; le titulaire garde le sien | ✅ | ✅ |
| E2E-AUDIT-001 | 1 | headless | Le titulaire lit au journal le message supprimé par son délégataire, au nom du délégataire | ✅ | — |
| E2E-AUDIT-002 | 1 | headless | Le journal d'audit montre chaque action sur un mail | ✅ | — |
| E2E-SHARED-001 | 1 | headless | Une boîte partagée, une base — le patient rattaché par le titulaire est vu du délégataire, la signature reste à chacun | ✅ | ✅ |
| E2E-SHARED-002 | 1 | headless | Le délégataire écrit pour le compte du titulaire — le destinataire voit qui a écrit, sa réponse revient à la boîte | ✅ | ✅ |
| E2E-SESSION-001 | 1 | headless | Naviguer dans Weda ne multiplie pas les sessions de messagerie | ✅ | — |
| E2E-SESSION-002 | 2 | headless | Quitter weda2 autonome ne ferme pas la session partagée | ✅ | — |
| E2E-SESSION-003 | 2 | headless | La session fermée par Weda fait quitter weda2 | ✅ | — |
| E2E-SESSION-004 | 1 | headless | Sur un appareil partagé, la personne suivante n'arrive jamais dans la boîte de la précédente | ✅ | ✅ |
| E2E-AI-002 | 1 | headless | Un délégataire interroge l'assistant dans la boîte qu'il a ouverte | ✅ | ✅ |
| E2E-MAILBOX-007 | 1 | headless | Après un changement de boîte, l'onglet Patients ne montre plus rien de la précédente | ✅ | ✅ |
| E2E-ERROR-001 | 1 | headless | Une erreur affiche un code et une référence à transmettre au support | ✅ | ✅ |

**Divergences temporaires ouvertes** (8) :

- E2E-SEARCH-001 [mobile] — le mobile adopte le formulaire à un seul niveau avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-004 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-005 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-006 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-007 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-009 [mobile] — le mobile adopte le mode résultats avec la refonte mobile de la recherche — résorbée par task-450
- E2E-SEARCH-010 [mobile] — la lecture enrichie arrive sur le mobile avec la refonte mobile — résorbée par task-451
- E2E-SEARCH-008 [mobile] — les critères médicaux arrivent sur le mobile avec la refonte mobile — résorbée par task-451

**Parité : verte** — aucun écart entre le catalogue et les suites.

## Develop log — reprise (CHANGES REQUESTED du /review)

- **A (bloquant)** `highlightHtml` : un fragment reste un fragment (`head.innerHTML` remis devant, `body.outerHTML` si le
  fragment portait un `<body>` à attributs) et le cadre isolé l'enveloppe comme avant (doctype, `charset`,
  `<base target="_blank">`) ; un document complet reste complet, avec son doctype d'origine (plus de doctype forcé).
  Pendant la reprise : renvoyer le document entier pour un fragment aurait perdu l'enveloppe du cadre et basculé le
  rendu en mode quirks — écarté, test « un fragment reste un fragment ».
- **B** `mail-body.plainSegments` mémoïsé par `{ texte, mots }`.
- **C** `findTermRanges` : un accent écrit à part (forme décomposée) après la dernière lettre reste dans la plage.
- Tests ajoutés, vus rouges avant le correctif : style en tête de fragment et attributs du corps gardés ; fragment
  rendu en fragment ; pas de doctype ajouté ; accent décomposé ; segments mémoïsés.
- Mutations : R1 en-tête du fragment perdu → 2 rouges ; R2 accent hors plage → 1 ; R3 recalcul à chaque rendu → 1 ;
  R4 fragment rendu en document → 1.
- Validation : `mss-lib` 1 604 verts, `weda2` 2 683, `nx build weda2` vert, ESLint 0 erreur. api-mail inchangé
  (`783ff7e1`, déjà vert : 7 788 tests).
- Prévention : `conventions/angular.md` « surlignage-par-positions », point sur la forme du HTML rendu, corrigé.
- Next step : /sonar task-446

- Reprise : api-mail inchangé (`783ff7e1`, déjà analysé ci-dessus, Quality Gate OK) — aucune nouvelle analyse.

- Reprise : lint `mss-lib` + `mss-e2e` rejoué sur l'arbre corrigé — 0 erreur, avertissements inchangés (52 / 48) ; mobile toujours non touché.

## Develop log — 2ᵉ reprise (A1)

- `hasDocumentHead(html)` (`text-highlight.util.ts`) : une seule définition de « HTML qui porte son en-tête »,
  partagée par `highlightHtml` et `medical-html-frame` (`wrapWithDesignTokens`). Le surlignage ne peut plus faire
  changer le cadre d'avis : un `<html><body>` sans `<head>`, avec ou sans doctype, reste enveloppé (liens ouverts à
  part, doctype, viewport) ; un `<head>` dans un commentaire est jugé de la même façon avant et après.
- Tests : `medical-html-frame.component.spec.ts` « corps surligné (task-446) » — pour cinq formes (fragment, document
  sans en-tête, doctype sans en-tête, en-tête en commentaire, document complet), le cadre enveloppe le HTML surligné
  **comme sans surlignage** ; document à en-tête : jetons injectés, en-tête gardé. Vus rouges sur le code d'avant
  (2 formes).
- Mutations : R5 surlignage revenu à l'ancien test (`<html`) → 2 rouges ; R6 cadre jugeant autrement → 2 rouges.
- Validation : `mss-lib` 1 610 verts, `weda2` 2 683, `nx build weda2` vert, ESLint 0 erreur (avertissements
  préexistants du cadre). api-mail inchangé (`783ff7e1`).
- Next step : /sonar task-446

## PRs

- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/362 — label `awaiting-human-merge`
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR, sur `feature/nova-mss-weda-integration`.
  ⚠️ **À commiter avant le merge de #362** : `functional.e2e.ts` (E2E-SEARCH-010 ; 004 à 009 de task-445 s'ils ne le
  sont pas). L'arbre porte aussi le travail non commité de task-442/443/445. Fichiers modifiés ou nouveaux sous `front/` :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/e2e/mss-e2e/support/e2e-backend.ts`
  - `front/libs/mss/src/core/models/search.model.ts`
  - `front/libs/mss/src/core/services/mss-api.service.ts`
  - `front/libs/mss/src/features/mail/components/mail-body/mail-body.component.html`
  - `front/libs/mss/src/features/mail/components/mail-body/mail-body.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-body/mail-body.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-body/mail-body.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.html`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.on-behalf-of.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.read-receipt.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.side-panel.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.stale-content.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.html`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.list-sources.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-search/mail-search.component.html`
  - `front/libs/mss/src/features/mail/components/mail-search/mail-search.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-search/mail-search.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-search/mail-search.component.ts`
  - `front/libs/mss/src/features/mail/components/medical-html-frame/medical-html-frame.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/medical-html-frame/medical-html-frame.component.ts`
  - `front/libs/mss/src/features/mail/mss-mail.component.list-sources.spec.ts`
  - `front/libs/mss/src/features/mail/services/mail-state.service.ts`
  - `front/libs/mss/src/features/settings/mss-settings.component.html`
  - `front/libs/mss/src/features/settings/mss-settings.component.scss`
  - `front/libs/mss/src/features/settings/mss-settings.component.spec.ts`
  - `front/libs/mss/src/features/settings/mss-settings.component.ts`
  - `front/libs/mss/src/core/utils/text-highlight.util.spec.ts`
  - `front/libs/mss/src/core/utils/text-highlight.util.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.search-highlight.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-list/mail-list.search-mode.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-search-results/mail-search-results.component.html`
  - `front/libs/mss/src/features/mail/components/mail-search-results/mail-search-results.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-search-results/mail-search-results.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-search/_mail-search-combobox.scss`
  - `front/libs/mss/src/features/mail/components/mail-search/mail-search-patient-picker/mail-search-patient-picker.component.html`
  - `front/libs/mss/src/features/mail/components/mail-search/mail-search-patient-picker/mail-search-patient-picker.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-search/mail-search-patient-picker/mail-search-patient-picker.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-search/mail-search-picker.scss`
  - `front/libs/mss/src/features/mail/components/mail-search/mail-search-sender-picker/mail-search-sender-picker.component.html`
  - `front/libs/mss/src/features/mail/components/mail-search/mail-search-sender-picker/mail-search-sender-picker.component.ts`
  - `front/libs/mss/src/features/mail/services/mail-search-session.spec.ts`
  - `front/libs/mss/src/features/mail/services/mail-search-session.ts`
  - `front/libs/mss/src/features/mail/services/mail-search-tags.spec.ts`
  - `front/libs/mss/src/features/mail/services/mail-search-tags.ts`

## Code Review Summary

**APPROVED** (3ᵉ passage) — 0 bloquant.

- Passage 1 : CHANGES REQUESTED — `highlightHtml` perdait le `<style>` de tête d'un fragment et les attributs de
  `<body>` (A) ; suggestions B (texte brut recalculé à chaque rendu) et C (accent décomposé hors plage). Corrigés,
  tests R1-R4 rouges sous mutation.
- Passage 2 : CHANGES REQUESTED — le correctif de A faisait sortir un `<html><body>` sans `<head>` de l'enveloppe du
  cadre (A1). Corrigé par `hasDocumentHead`, partagé par le surlignage et le cadre ; tests R5-R6 rouges.
- Passage 3 : APPROVED (revue indépendante) — fix A1 correct, tests capables d'échouer.
- Validation : api-mail `783ff7e1` 7 788 tests verts, Sonar QG OK ; weda2 `mss-lib` 1 610, `weda2` 2 683, build vert ;
  e2e mobile 60 (réutilisée), angular 80, parité verte.
- Règle 1b : aucun comportement d'endpoint modifié ; parcours weda2 prouvé par E2E-SEARCH-010 (F1-F4 rouges).
- Suggestion non bloquante, défaut **antérieur** : `hasDocumentHead` (ex-test du cadre) reconnaît `<header>` ; un
  fragment qui en contient n'est jamais enveloppé. Task de suivi recommandée (`/<head[\s>]/i` + test).
- Prévention : `conventions/angular.md` « surlignage-par-positions » (positions et texte échappé ; forme du HTML ; même
  test de forme que l'hôte).

## Timings

*(généré par `tools/timing/report.sh --task task-446 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 14 s | — | — | — | — |
| /develop | ok | 3 min 45 s | 4 (1 min 01 s) | 4 (7 min 24 s) | — | api-mail 1B/1T, client-angular 3B/3T, reprise 2 : A1 |
| /sonar | skipped | 0.4 s | 1 (24 s) | 5 (8 min 04 s) | 2 (54 s) | api-mail 1B/5T, api-mail inchangé depuis l'analyse de 783ff7e1 (QG OK) |
| /lint-angular | ok | 12 s | — | — | — | — |
| /lint-mobile | skipped | 0.5 s | — | — | — | client-mobile non touché |
| /e2e | ok | 10 min 19 s | — | — | — | e2e ×9 (39 min 54 s), reprise 2 : mobile réutilisée, angular 80 verts |
| /review | ok | 51 s | 1 (17 s) | 1 (5 min 51 s) | — | api-mail 1B/1T |
| **Total cycle** | | **15 min 24 s** | **6 (1 min 42 s)** | **10 (21 min 20 s)** | **2 (54 s)** | |

Autres commandes mesurées : lint ×3 (1 min 16 s)
