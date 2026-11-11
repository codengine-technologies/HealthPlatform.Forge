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

## Timings

*(généré par `tools/timing/report.sh --task task-446 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 14 s | — | — | — | — |
| /develop | ok | 27 min 29 s | 2 (30 s) | 2 (6 min 19 s) | — | api-mail 1B/1T, client-angular 1B/1T |
| /sonar | ok | 9 min 53 s | 1 (24 s) | 5 (8 min 04 s) | 2 (54 s) | api-mail 1B/5T |
| /lint-angular | ok | 1 min 03 s | — | — | — | — |
| /lint-mobile | skipped | 0.4 s | — | — | — | client-mobile non touché |
| **Total cycle** | | **38 min 41 s** | **3 (54 s)** | **7 (14 min 24 s)** | **2 (54 s)** | |

Autres commandes mesurées : lint ×1 (53 s)
