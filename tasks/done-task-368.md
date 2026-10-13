# todo-task-368.md — Un contenu reçu ne s'exécute jamais dans weda2 : pièces jointes, documents CDA et synthèses IA sont rendus cloisonnés

**Repos**: client-angular, client-mobile, api-mail, interop-cda
**Dependencies**: — (aucune)
**Epic**: E009
**Single frontend**: false — weda2 et le mobile (décision humaine du 2026-10-13).
**Priorité**: **0** — n'importe quel émetteur du réseau MSSanté peut faire exécuter du script dans la session du médecin : vol de session, lecture de toute la boîte et des dossiers patients, envoi de mails en son nom.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-01 ✔, ANG-02 ✔, ANG-03 ✔, ANG-04, ANG-38, ANG-39**),
> version auditée `feature/nova-rewriting-mss-weda-integration` @ `84c2e6ac`.

## Ce qui est établi

- **Aucune CSP `script-src`** : `Client/Angular/front/nginx.conf` ne pose que `frame-ancestors`. Tout HTML exécuté dans l'origine weda2 a les pleins pouvoirs (accès à `parent`, appels à api-mail avec le jeton du médecin).
- **ANG-01** — `mail-detail.component.ts:595-602, 626-640` : une pièce `text/*` est prévisualisée dans une `iframe` **sans `sandbox`** (`mail-detail.component.html:676-697`), à partir d'un blob dont le type vient du serveur, donc de l'expéditeur (`MailController.cs:832`). Une pièce `compte-rendu.html` s'exécute au simple clic sur sa ligne.
- **ANG-02** — `medical-html-frame.component.ts:28-34, 120-128` : le HTML CDA est chargé dans une `iframe` de même origine, sans `sandbox`. La XSL `interop.cda.parser/src/Interop.Cda/resources/html/style.xsl:419-437` recopie **tous** les attributs des tableaux (`<xsl:copy-of select="@*"/>`), donc un `onmouseover` ; `CdaParsingService.cs:569-599` n'assainit pas ce HTML. Un lien `target="_top"` d'un corps de mail (autorisé par `HtmlBodySanitizer`) remplace tout l'onglet weda2.
- **ANG-03** — `medical-document-modal.component.ts:95-97` : le même HTML CDA est injecté dans le document principal via `bypassSecurityTrustHtml`.
- **ANG-04** — `ai-chat-panel.component.ts:246-249`, `mail-summary.component.ts:113-119`, `ui/mail-summary/mail-summary.component.ts:229-231` : la sortie des modèles (markdown) passe par `marked` puis `bypassSecurityTrustHtml`. Une injection de prompt dans un mail reçu est recopiée, persistée, et affichée sans clic par le widget de notifications.
- **ANG-38, ANG-39** — Le blocage des images distantes (`remote-content.util.ts:12-17`) se contourne (`url(&quot;…&quot;)` produit par AngleSharp, `image-set()`), et ne s'applique ni aux CDA ni à la vue en lecture seule : l'expéditeur apprend que le médecin a ouvert le mail.

## Objective

Qu'**aucun contenu venu de l'extérieur** — pièce jointe, document CDA, corps de mail, sortie d'un modèle d'IA — ne puisse exécuter de script, naviguer la page de weda2 ou charger une ressource distante sans le consentement du médecin, quelle que soit la façon dont il est ouvert.

### Périmètre

1. **Aperçu des pièces jointes** : prévisualisation en `iframe` réservée au PDF et aux images ; le texte est forcé en `text/plain` ; toute autre pièce se télécharge. Côté api-mail, `Content-Disposition: attachment` et `X-Content-Type-Options: nosniff` sur le téléchargement.
2. **`medical-html-frame`** : `sandbox` sans `allow-scripts` ni `allow-same-origin` (les liens peuvent s'ouvrir en dehors : `allow-popups allow-popups-to-escape-sandbox`). Le commentaire « iframe sandboxée » de `mail-read-only-view` devient vrai.
3. **Fenêtre du document patient** : rendue par `medical-html-frame`, plus aucun `bypassSecurityTrustHtml`.
4. **Sorties d'IA** : plus aucun `bypassSecurityTrustHtml` ; HTML brut désactivé dans `marked`, et sortie assainie (assainisseur Angular ou DOMPurify).
5. **HTML CDA à la source** : la XSL ne recopie plus que les attributs autorisés par le schéma CDA (plus de `copy-of @*` ni de recopie de `link_html/@*`), et api-mail assainit le HTML CDA comme le corps des mails.
6. **Contenu distant** : blocage appliqué sur le DOM analysé (et non par regex) à tous les rendus HTML, CDA compris, avec la bannière « Afficher les images ».
7. **CSP** : `script-src` (et `img-src` pour l'`iframe` de rendu) dans `nginx.conf`, compatible avec le build Angular.

> **⚠️ Arbitrage humain requis — le client mobile.** Le mobile (`client-mobile`) n'a pas été audité. Il
> affiche lui aussi pièces jointes, CDA et synthèses IA. Faut-il (a) l'auditer et l'inclure dans cette
> task (ajout de `client-mobile` aux `**Repos**`), ou (b) ouvrir une task mobile dédiée ? La forge pose
> la question au `/start` et ne tranche pas.
>
> **Décision humaine (2026-10-13, avant `/forge 368 to 381`) : inclure le mobile.** `/develop` audite le
> même périmètre sur `client-mobile` et y corrige les défauts trouvés ; les scénarios e2e de la task sont
> `requis` sur angular **et** mobile.
>
> **Décision humaine (2026-10-13) : CSP hors task.** Le point 7 du périmètre (CSP `script-src` dans
> `nginx.conf`) est retiré de cette task ; il fera l'objet d'une task à part. La ligne « CSP » n'entre pas
> dans la DOD.

### Hors périmètre

- La validation XSD / Schematron des CDA reçus à l'ingestion (garde-fou métier distinct, à suivre à part si elle manque).

## Definition of Done

- [x] Build et tests verts : weda2 (`npm run build`, `npm test`), api-mail, interop-cda
- [x] Tests unitaires rouges d'abord, client-angular :
  - [x] une pièce `text/html`, `text/xml` ou `application/xhtml+xml` n'est jamais rendue en `iframe` ; une pièce `text/plain` l'est en `text/plain`
  - [x] toute `iframe` de rendu (aperçu, `medical-html-frame`) porte `sandbox` sans `allow-scripts` ni `allow-same-origin`
  - [x] aucune occurrence de `bypassSecurityTrustHtml` sur un contenu reçu ou généré (test d'architecture par recherche dans les sources)
  - [x] le blocage du contenu distant traite `url(&quot;…&quot;)`, `image-set()` et les attributs `style` des CDA
- [x] Test d'intégration de bout en bout pour `GET /api/v1/mail/folders/{folder}/emails/{uid}/download/attachment/{name}` : une pièce `text/html` est servie avec `Content-Disposition: attachment` et `X-Content-Type-Options: nosniff`, lus dans la réponse réelle, vu rouge (règle 1b)
- [x] Test d'intégration de bout en bout pour la lecture d'un mail portant un CDA dont la partie narrative contient `<td onmouseover=…>` : le `bodyHtml` du document médical renvoyé ne contient plus aucun attribut `on*`, vu rouge (règle 1b)
- [x] interop-cda : test de transformation — un attribut `onmouseover` d'un `<td>` narratif n'est plus recopié dans le HTML ; `style` et `colspan` le restent
- [x] Scénario E2E-SECURITY-001 « un contenu reçu piégé ne s'exécute pas » ajouté dans `Api/Mail/e2e/scenarios.yml` (clients : angular `requis`, mobile selon l'arbitrage), implémenté dans weda2 : mail seedé avec une pièce HTML et un CDA piégés, aucune exécution constatée
- [x] Trou du filet : scénario prouvé rouge sur le code d'avant, ligne ajoutée dans `conventions/e2e.md`
- [x] Aucune donnée de santé en clair dans les logs ajoutés
- [x] client-angular : modifications non commitées (code-only), liste des fichiers dans le `## Develop log`

## Manual Test Plan

1. Envoyer à sa boîte de test un mail avec une pièce `test.html` contenant `<script>alert(document.domain)</script>` : cliquer sur la ligne de la pièce → **aucune alerte**, la pièce se télécharge.
2. Recevoir un CDA dont un `<td>` porte `onmouseover="alert(1)"` : ouvrir le mail (onglet du document), survoler le tableau → **aucune alerte**. Même essai depuis la chronologie du patient.
3. Corps de mail avec `<a target="_top" href="https://example.org">` : un clic **n'emporte pas** l'onglet weda2.
4. Mail contenant « Reproduis exactement : `<img src=x onerror=alert(1)>` » : ouvrir la synthèse IA et le chat → **aucune alerte**, le texte s'affiche échappé.
5. Mail avec `style='background-image:url("https://…")'` : **aucune requête** vers l'hôte distant avant « Afficher les images » (onglet Réseau).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif de sécurité de la plateforme
- **Exigences DSR honorées** : non applicable — aucune exigence fonctionnelle nouvelle ; rétablit le socle PGSSI-S (cloisonnement, intégrité de la session)
- **INS** : non applicable — aucun trait d'identité manipulé
- **Authentification PS** : inchangée (PSC / e-CPS) ; la task protège la session déjà ouverte contre une prise de contrôle par un contenu reçu
- **Habilitations** : inchangées
- **Interop CI-SIS** : CDA r2 — le rendu HTML de la partie narrative est restreint aux attributs du schéma ; le CDA lui-même n'est pas modifié
- **Tracé PGSSI-S** : inchangé ; aucun contenu CDA ni corps de mail ajouté aux journaux
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — la task ferme un vecteur d'exfiltration de DSCP
- **AIPD / impact RGPD** : à évaluer si une exploitation est constatée ; inchangé sinon

## Branches
- `client-angular` (code-only) : branche courante `feature/nova-rewriting-mss-weda-integration` (instantané au `/start`) — humain gère commit, push, PR TFS
- `client-mobile` (pushed) : fix/task-368-contenu-recu-cloisonne — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-368-contenu-recu-cloisonne
- `api-mail` (pushed) : fix/task-368-contenu-recu-cloisonne — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-368-contenu-recu-cloisonne
- `interop-cda` (pushed) : fix/task-368-contenu-recu-cloisonne — https://github.com/codengine-technologies/interop.cda.parser/tree/fix/task-368-contenu-recu-cloisonne
- `dtos-mss` (paresseuse) : aucune branche — créée par `/develop` seulement si un contrat change

## Develop log

### Décisions

- **Mobile inclus** (décision humaine du 2026-10-13) : même périmètre audité et corrigé sur `client-mobile`.
- **CSP hors task** (décision humaine) : point 7 du périmètre non traité, à ouvrir en task dédiée.
- **PDF embarqués d'un CDA** : une sonde Chrome (cadre sans sandbox / sandbox avec `allow-same-origin` / sandbox strict) a montré que Chrome n'affiche **aucun** PDF imbriqué dans un cadre sandboxé. weda2 sort donc les PDF du document et les affiche chacun dans son cadre hôte, depuis un blob `application/pdf` ; le HTML, lui, est en sandbox strict. Le mobile n'extrait pas (les WebView n'affichent pas de PDF en iframe) : à vérifier sur iOS au plan de test.
- **Défense en profondeur, trois couches** : la XSL ne recopie plus que les attributs du schéma CDA (interop 109) ; api-mail assainit le HTML d'un document à **la lecture** (couvre les documents stockés avant le correctif) ; les clients le rendent en cadre sandboxé.
- **Blocage du contenu distant** : déplacé dans `medical-html-frame` (weda2 et mobile), donc appliqué à tout rendu HTML (corps, CDA, vue en lecture seule, fenêtre du document patient), avec la bannière « Afficher les images », remise à zéro à chaque nouveau document.

### Livré

| Repo | Commit | Contenu |
|---|---|---|
| interop-cda | `299c9af` (CI #109 publiée) | `style.xsl` html et texte : attributs du narratif en liste blanche ; liens `cda_asip.xsl` / `cda_custom.xsl` : `name`, `title`, `href` http(s)/mailto seulement |
| api-mail | `46be1829` | `Interop.Cda.Parser` 107 → 109 |
| api-mail | `a23bd2d4` | `SanitizeMedicalDocument`, appliqué dans `MailRepository` (2 mappeurs) et `PatientRepository` ; seed e2e piégé ; catalogue E2E-SECURITY-001 |
| client-mobile | `de54dce` | cadre sandboxé + blocage distant + bannière ; fenêtre du document patient par le cadre ; aperçu de la chronologie bloqué ; PDF retypés ; IA sans `bypassSecurityTrustHtml` (`align` au lieu de `style`) ; spec e2e E2E-SECURITY-001 |
| client-angular | non commité (code-only) | voir la liste ci-dessous |

**client-angular — fichiers modifiés (non commités, humain gère TFS)** :
`e2e/mss-e2e/specs/functional.e2e.ts`, `e2e/mss-e2e/specs/live-ai.e2e.ts`,
`libs/mss/src/core/utils/{ai-markdown.util.ts, ai-markdown.util.spec.ts, attachment-preview.util.ts, attachment-preview.util.spec.ts, remote-content.util.ts, remote-content.util.spec.ts}`,
`libs/mss/src/features/mail/components/{ai-chat-panel/ai-chat-panel.component.ts, mail-attachment/mail-attachment.component.{ts,spec.ts}, mail-body/mail-body.component.{ts,html,scss}, mail-detail/mail-detail.component.{ts,html,spec.ts}, mail-read-only-view/mail-read-only-view.component.html, mail-summary/mail-summary.component.ts, medical-html-frame/medical-html-frame.component.{ts,spec.ts}}`,
`libs/mss/src/features/patient/components/medical-document-modal/medical-document-modal.component.{ts,html,scss,spec.ts}`,
`libs/mss/src/ui/mail-summary/mail-summary.component.ts`.

### Preuves (règle 1b et tests rouges d'abord)

| Comportement | Test | Preuve du rouge |
|---|---|---|
| Lecture d'un mail portant un document au HTML piégé : `bodyHtml` sans contenu actif, mise en forme gardée | `FolderOperationsEndToEndTests.ReadingAMail_ServesItsMedicalDocumentHtml_FreeOfActiveContent_AndKeepsItsLayout` (TestServer, base réelle) | rouge avant correctif ; **mutation M1** (`MedicalDocumentHtml.Sanitize` rendu identité) → rouge |
| Pièce `text/html` servie en `attachment` + `nosniff` | `MailAttachmentDownloadIntegrationTests.DownloadAttachment_OfAnHtmlPart_IsServedAsAnAttachmentToSave` | **non-régression** : vert dès l'écriture, les en-têtes existaient déjà ; le test verrouille le comportement |
| Liste : `BodyHtml` d'un document reste `null` | `HeaderListingProjectionTests` (existant) | rouge pendant le développement (`""` au lieu de `null`), corrigé dans `MedicalDocumentHtml` |
| XSL : `onmouseover` / `onclick` / `javascript:` non recopiés, `style` / `colspan` gardés | `CdaHtmlNarrativeAttributeTests` (interop) | rouge avant correctif |
| Pipeline CDA du seed e2e : la cellule piégée sort sans gestionnaire | `E2eUnattachedXdmTests.TheSeededCda_CarriesATrappedCell_ThatTheCdaPipelineDoesNotRender` | précondition dans le test (le fixture porte `onmouseover`) ; rouge avec interop 107 (même transformation que `CdaHtmlNarrativeAttributeTests`) |
| weda2 : aperçu réservé à PDF / images (hors SVG) / texte forcé `text/plain` | `attachment-preview.util.spec`, `mail-attachment`, `mail-detail` specs | rouges d'abord |
| weda2 : cadre sandboxé, PDF sortis du document | `medical-html-frame.component.spec` | rouges d'abord |
| weda2 : contenu distant bloqué dans le cadre, révélé à la demande, rebloqué au document suivant | `medical-html-frame.component.spec` | rouges d'abord ; **mutation** (blocage retiré du cadre) → 2 rouges |
| weda2 : fenêtre du document patient par le cadre, PDF retypé | `medical-document-modal.component.spec` | rouges d'abord |
| weda2 : markdown IA sans HTML brut ; aucun `bypassSecurityTrustHtml` dans `libs/mss` | `ai-markdown.util.spec` (test d'architecture par lecture des sources) | rouges d'abord ; **mutation** (ligne ajoutée dans `ui/mail-summary`) → rouge nommant le fichier |
| weda2 : blocage DOM — `&quot;`, `image-set()`, sans guillemets, sans schéma, `srcset`, `poster`, `<style>`, `@import`, CDA | `remote-content.util.spec` | 8 rouges d'abord |
| mobile : mêmes comportements (blocage DOM, cadre sandboxé, PDF retypés, fenêtre patient, aperçu chronologie, `align`) | specs Karma correspondantes | rouges d'abord ; fenêtre patient : test de **rendu réel** (Ionic initialisé), rouge sur l'ancien gabarit (`div` au lieu du cadre) |

Les mutations ont été annulées **depuis une copie** (convention `restauration-de-mutation`).

### Validation

- interop-cda : 503 tests verts (`--no-incremental`, voir convention `ressource-resx-perimee`).
- api-mail : suite complète verte — 190 + 690 + 1229 + 3635 + 884 (16 ignorés).
- weda2 : `npm run build` vert ; `npm test` vert (11 projets, dont `mss` 814).
- mobile : `npm run build` vert ; `ng lint` sans erreur ; Karma 1049 verts.
- Suites e2e compilées : `npx tsc -p e2e/tsconfig.json` (mobile) et `npx tsc -p e2e/mss-e2e/tsconfig.json` (Angular), vertes.

### E2E-SECURITY-001

Seed : `mail-piege` (pièce `compte-rendu-piege.html` dont le script renommerait l'onglet `E2E-PIEGE`) et cellule « Statut du document » piégée (`onmouseover`) dans le CDA sans INS. Specs : weda2 (`functional.e2e.ts`) et mobile (`functional.spec.ts`), précondition du négatif lue avant chaque absence (pièce reçue / montrée en texte ; cellule affichée). La preuve rouge sur le code d'avant est faite à l'étape `/e2e`.

### Passe qualité (§Q)

Relue sur les trois repos : rien à simplifier. La duplication `remote-content.util` weda2 / mobile est le miroir voulu (parité des clients). Suggestion pour la revue : l'assainissement à la lecture analyse le HTML de chaque document servi (AngleSharp) ; coût accepté pour couvrir les documents déjà stockés.

### Leçons

- `conventions/angular.md` › `pdf-en-cadre-sandboxe` (nouvelle).
- `conventions/csharp.md` › `ressource-resx-perimee` (nouvelle).
- `conventions/e2e.md` › `suite-e2e-non-compilee` : occurrence 3, attrapée par le `tsc` avant commit.

## Sonar log

- Mode A (chaîné), serveur SonarQube 9.9.8 (`sonar.login`), projet `healthplatform-api-mail`, période de nouveau code « version précédente ». 1 analyse complète (build Release, 5 passes OpenCover : 190 + 3635 + 690 + 1229 + 884 verts).
- Phase 1 (new code) : ✓ Quality Gate OK, new_coverage = 97,1 % (cible 95 %). Code neuf de la task : `HtmlBodySanitizer` 97,6 % (0 ligne non couverte), `MedicalDocumentHtml` 100 %.
- Phase 1 — Issues fixées : 0 (aucune levée) ; hotspots : 0. Tests ajoutés : 0 (couverture déjà au-dessus de la cible).
- Phase 2 (legacy) : 0 itération — aucune dette ouverte (0 code smell).
- Build / tests : ✓ green.
- `conventions/csharp.md` : rien à alimenter (aucune règle corrigée).

### KPIs qualité (baseline → final)

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | → |
| New coverage | 97,1 % | 97,1 % | 0 |
| Bugs | 0 | 0 | 0 |
| Vulnerabilities | 0 | 0 | 0 |
| Security hotspots | 0 | 0 | 0 |
| Code smells | 0 | 0 | 0 |
| Coverage (projet) | 98,0 % | 98,0 % | 0 |
| Duplication | 0,4 % | 0,4 % | 0 |
| Reliability / Security / Maintainability | A/A/A | A/A/A | → |

## Lint log

- Mode A, base `origin/next`, portée lint `tag:scope:mss`. 1 itération.
- Base : 10 erreurs, 50 avertissements. Les 10 erreurs étaient toutes dans le code de la task : 6 `prettier/prettier` (`remote-content.util.ts`, `attachment-preview.util.ts`, `mail-detail.component.ts`), 4 `jsdoc/require-jsdoc` sur les fonctions privées des utilitaires.
- JSDoc écrite à la main (`ai-markdown.util.ts`, `remote-content.util.ts`), puis `--fix` pour prettier. Final : **0 erreur**, 50 avertissements `jsdoc/require-example`, tous antérieurs (aucun dans un fichier créé par la task).
- Aucun fichier reformaté en entier (convention `prettier-fichier-existant`, diffs vérifiés par `git diff --numstat`).
- Build affecté : `weda2` ✓ (avertissement de budget : bundle initial 2,01 Mo pour 2 Mo). `mss:build:production` ✗, **dette existante hors task** : `apps/mss/project.json` remplace `apps/mss/src/environments/environment.prod.ts`, fichier jamais versionné.
- Tests affectés : ✓ (11 projets). Suite e2e Angular recompilée (`tsc`) : ✓.
- client-angular reste non commité (code-only).

## Lint mobile log

- Mode A, branche `fix/task-368-contenu-recu-cloisonne` @ `de54dce`, arbre propre.
- Base : **0 erreur, 0 avertissement** (`npm run lint` : « All files pass linting »). 0 itération, aucun commit.
- Build et tests déjà verts sur cet état (`/develop` : `npm run build` ✓, Karma 1049 ✓).

## E2E log

| Voie | Déclencheur | Résultat | Tests | Durée |
|---|---|---|---|---|
| mobile | api-mail, client-mobile touchés | ✅ verte | 35 verts, 0 flaky, 0 rouge | 6 min 21 s |
| angular | api-mail, client-angular touchés | ✅ verte | 39 verts, 0 flaky, 0 rouge, 1 quarantaine (E2E-COMPOSE-002, humain) | 6 min 32 s |

- Catalogue : `Api/Mail/e2e/scenarios.yml` @ `fix/task-368-contenu-recu-cloisonne` (E2E-SECURITY-001 ajouté, données `mail-piege` et cellule piégée du CDA sans INS).
- Voie Angular rejouée après le durcissement de son spec (voir ci-dessous) ; la porte lit ce second rapport.
- Rapports copiés dans la même commande que leur voie.
- Parcours touchés sans spec e2e modifié : aucun (les deux suites portent E2E-SECURITY-001).
- Démontage : complet (ports libres, aucun conteneur e2e résiduel).

### Preuve rouge d'E2E-SECURITY-001 (trou du filet)

Code d'avant reconstitué : api-mail sur Interop 107, assainissement à la lecture neutralisé ; chaque client servi en `--serve-only`, scénario seul, sans nouvel essai. Mutations annulées depuis des copies (clients) et par `git checkout` (api-mail, entièrement commité), diffs vérifiés.

| Client | Mutation | Résultat |
|---|---|---|
| weda2 | aperçu d'avant (`text/*` prévisualisé, blob au type servi, cadre sans `sandbox`) | ✗ rouge sur « le script de la pièce ne s'est pas exécuté » (onglet `E2E-PIEGE`) ; deux autres passages ✗ sur l'ancre « la pièce piégée a été traitée » (l'aperçu d'avant ne s'affiche pas toujours) |
| weda2 | cadre du document sans `sandbox` | ✗ rouge sur « le gestionnaire de la cellule ne s'est pas exécuté » ; étape pièce verte (correctif) |
| mobile | cadre sans `sandbox` ni nettoyage client | ✗ rouge sur « le gestionnaire de la cellule ne s'est pas exécuté » |

Le premier passage weda2 (pièce) est resté **vert** sur le code vulnérable : la lecture se faisait après un délai fixe de 1,5 s, et à froid l'aperçu s'affichait après lui. Le spec attend désormais un signal positif (téléchargement, ou corps du cadre d'aperçu) avant de lire l'absence ; leçon `negatif-a-delai-fixe` dans `conventions/e2e.md`. Sur mobile, la pièce était déjà montrée comme du texte avant la task : l'étape le verrouille (le texte du script est affiché).

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
| E2E-CONTACT-001 | 1 | humain | Rechercher dans le carnet et interroger l'annuaire national | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-SETTINGS-001 | 1 | headless | Changer le filtre par défaut et le retrouver après rechargement | ✅ | ✅ |
| E2E-MAIL-001 | 1 | headless | Marquer un message lu puis non lu | ✅ | ✅ |
| E2E-MAIL-002 | 1 | headless | Tout sélectionner et marquer lu en masse | ✅ | ✅ |
| E2E-DETAIL-001 | 2 | headless | Répondre et transférer depuis la lecture d'un message | ✅ | ✅ |
| E2E-COMPOSE-001 | 1 | headless | Envoyer un message, le recevoir, le lire, le supprimer | ✅ | ✅ |
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ✅ | ✅ |
| E2E-COMPOSE-003 | 1 | headless | Un envoi refusé par la messagerie laisse le brouillon intact et peut être renvoyé | ✅ | ✅ |
| E2E-MAIL-003 | 1 | headless | Signaler puis ne plus signaler un message | ✅ | ✅ |
| E2E-MAIL-004 | 1 | headless | Déplacer un message vers Archive puis le ramener | ✅ | ✅ |
| E2E-MAIL-005 | 1 | headless | Un message supprimé depuis un autre logiciel quitte la liste et ne s'ouvre jamais vide | ✅ | ✅ |
| E2E-DRAFT-001 | 1 | headless | Créer un brouillon, le reprendre, le supprimer | ✅ | ✅ |
| E2E-DRAFT-002 | 1 | headless | Envoyer un message à pièce jointe après l'enregistrement automatique du brouillon | ✅ | ✅ |
| E2E-BIO-001 | 1 | headless | Acquitter un compte rendu de biologie | ✅ | ✅ |
| E2E-DASH-001 | 1 | headless | Afficher les widgets du tableau de bord | ✅ | ✅ |
| E2E-DETAIL-002 | 1 | headless | Basculer entre texte brut et HTML à la lecture | ✅ | ✅ |
| E2E-DETAIL-003 | 1 | headless | Répondre à tous depuis la lecture d'un message | ✅ | ✅ |
| E2E-DETAIL-004 | 1 | headless | Lire un message avec le panneau d'actions, le masquer puis le retrouver au message suivant | ✅ | — |
| E2E-SETTINGS-002 | 1 | headless | Changer la vue par défaut et la retrouver après rechargement | ✅ | ✅ |
| E2E-SEARCH-001 | 1 | headless | Rechercher un message et ouvrir la recherche avancée | ✅ | ✅ |
| E2E-ATTACH-001 | 1 | headless | Voir les pièces jointes d'un message | ✅ | ✅ |
| E2E-CONTACT-002 | 1 | headless | Créer puis supprimer un contact | ✅ | ✅ |
| E2E-SIGNATURE-001 | 1 | headless | Créer puis supprimer une signature | ✅ | ✅ |
| E2E-CONTACT-003 | 1 | headless | Créer puis supprimer un groupe de contacts | ✅ | ✅ |
| E2E-FOLDER-002 | 1 | headless | Créer puis supprimer un dossier | ✅ | ✅ |
| E2E-FOLDER-003 | 1 | headless | Ouvrir un dossier supprimé depuis un autre logiciel | ✅ | ✅ |
| E2E-FOLDER-004 | 1 | headless | Actualiser la liste des dossiers après un changement fait dans un autre logiciel | ✅ | ✅ |
| E2E-AUTH-001 | 1 | humain | Rester connecté quand le jeton d'accès expire | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-AUTH-002 | 1 | humain | Se déconnecter | 👤 non joué (humain) | 👤 non joué (humain) |
| E2E-LIVE-001 | 1 | headless | Recevoir un nouveau message en temps réel, sans recharger | ✅ | ✅ |
| E2E-AI-001 | 1 | headless | Interroger l'assistant sur des messages sélectionnés et poser des questions de suite | ✅ | ✅ |
| E2E-WEDA-001 | 1 | headless | Dans Weda, la messagerie s'ouvre sur la boîte que Weda désigne | ✅ | — |
| E2E-WEDA-002 | 1 | headless | Voir le dossier Weda du patient d'un document reçu, l'ouvrir, puis importer des documents dans un dossier | ✅ | — |
| E2E-WEDA-003 | 1 | headless | Envoyer un document du dossier patient Weda par la nouvelle messagerie | ✅ | — |
| E2E-RECEIPT-001 | 1 | headless | Demander un accusé de lecture à l'envoi | ✅ | ✅ |
| E2E-RECEIPT-002 | 1 | headless | Envoyer l'accusé de lecture d'un message reçu, une seule fois | ✅ | ✅ |
| E2E-RECEIPT-003 | 1 | headless | Refuser l'accusé de lecture d'un message reçu | ✅ | ✅ |
| E2E-SECURITY-001 | 1 | headless | Un contenu reçu piégé ne s'exécute pas | ✅ | ✅ |

**Parité : verte** — aucun écart entre le catalogue et les suites.

## PRs

- interop-cda : https://github.com/codengine-technologies/interop.cda.parser/pull/11 (label awaiting-human-merge)
- api-mail : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/293 (label awaiting-human-merge) — à merger **après** interop-cda #11 (Interop.Cda.Parser 109 déjà publié)
- client-mobile : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/92 (label awaiting-human-merge)
- client-angular : code-only — humain gère commit/push TFS et ouverture PR, branche `feature/nova-rewriting-mss-weda-integration`. Fichiers modifiés :

```
front/e2e/mss-e2e/specs/functional.e2e.ts
front/e2e/mss-e2e/specs/live-ai.e2e.ts
front/libs/mss/src/core/utils/remote-content.util.spec.ts
front/libs/mss/src/core/utils/remote-content.util.ts
front/libs/mss/src/features/mail/components/ai-chat-panel/ai-chat-panel.component.ts
front/libs/mss/src/features/mail/components/mail-attachment/mail-attachment.component.spec.ts
front/libs/mss/src/features/mail/components/mail-attachment/mail-attachment.component.ts
front/libs/mss/src/features/mail/components/mail-body/mail-body.component.html
front/libs/mss/src/features/mail/components/mail-body/mail-body.component.scss
front/libs/mss/src/features/mail/components/mail-body/mail-body.component.ts
front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.html
front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.spec.ts
front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.ts
front/libs/mss/src/features/mail/components/mail-read-only-view/mail-read-only-view.component.html
front/libs/mss/src/features/mail/components/mail-summary/mail-summary.component.ts
front/libs/mss/src/features/mail/components/medical-html-frame/medical-html-frame.component.ts
front/libs/mss/src/features/patient/components/medical-document-modal/medical-document-modal.component.html
front/libs/mss/src/features/patient/components/medical-document-modal/medical-document-modal.component.scss
front/libs/mss/src/features/patient/components/medical-document-modal/medical-document-modal.component.ts
front/libs/mss/src/ui/mail-summary/mail-summary.component.ts
front/libs/mss/src/core/utils/ai-markdown.util.spec.ts
front/libs/mss/src/core/utils/ai-markdown.util.ts
front/libs/mss/src/core/utils/attachment-preview.util.spec.ts
front/libs/mss/src/core/utils/attachment-preview.util.ts
front/libs/mss/src/features/mail/components/medical-html-frame/medical-html-frame.component.spec.ts
front/libs/mss/src/features/patient/components/medical-document-modal/medical-document-modal.component.spec.ts
```

- devops, psc-proxy-* : non concernés (managed manually by the human)

## Code Review Summary

**Verdict : APPROVED** — 0 bloquant, 6 suggestions. Validation `/review` : interop-cda 503 ✓ ; api-mail 190 + 690 + 1229 + 3635 ✓, intégration 880 / 884 (voir « Échecs hors task ») ; client-mobile build ✓, Karma 1049 ✓ ; weda2 `npm run build` ✓, `npm test` ✓ (11 projets).

### Règle 1b — comportement → test d'intégration → preuve du rouge

| Comportement (endpoint) | Test d'intégration | Preuve du rouge |
|---|---|---|
| Lecture d'un mail (`GET …/emails/content/{uid}`) : le `bodyHtml` d'un document médical piégé est servi sans contenu actif, mise en forme gardée | `FolderOperationsEndToEndTests.ReadingAMail_ServesItsMedicalDocumentHtml_FreeOfActiveContent_AndKeepsItsLayout` | rouge avant correctif ; mutation M1 (assainissement neutralisé) → rouge |
| Listes : le `BodyHtml` d'un document reste `null` | `HeaderListingProjectionTests.HeaderPageStillRendersAttachmentsAndDocumentsIdentically` (existant) | rouge pendant le développement (`""`), corrigé |
| Téléchargement d'une pièce `text/html` : `Content-Disposition: attachment` | `MailAttachmentDownloadIntegrationTests.DownloadAttachment_OfAnHtmlPart_IsServedAsAnAttachmentToSave` | non-régression (comportement déjà en place, verrouillé) |
| `X-Content-Type-Options: nosniff` sur toute réponse | `SecurityHeadersIntegrationTests` (existant) | existant |
| Transformation CDA → HTML (bibliothèque, pas d'endpoint) | `CdaHtmlNarrativeAttributeTests`, `E2eUnattachedXdmTests.TheSeededCda_…` | rouge avant correctif (interop) |

### Par repo

- **interop-cda** — `style.xsl` (html, texte) : attributs du narratif en liste blanche du schéma CDA ; `cda_asip.xsl` / `cda_custom.xsl` : liens réduits à `name`, `title`, `href` http(s)/mailto. ✅
- **api-mail** — `HtmlBodySanitizer.SanitizeMedicalDocument` (document complet, PDF `data:` gardés), appliqué dans les mappeurs de lecture (`MailRepository` ×2, `PatientRepository`). ✅ Couvre aussi les documents stockés avant le correctif, et le client Blazor, qui affiche le même HTML.
- **client-mobile** — cadre sandboxé + blocage distant + bannière ; fenêtre du document patient par le cadre ; aperçu de chronologie bloqué ; PDF retypés ; IA sans contournement de l'assainisseur. ✅
- **client-angular** (non commité) — idem côté weda2, plus extraction des PDF hors du cadre sandboxé (Chrome ne les affiche pas dedans), aperçu des pièces réservé à PDF / images / texte, test d'architecture contre `bypassSecurityTrustHtml`. ✅

### Suggestions (non bloquantes)

1. ⚠️ api-mail — l'assainissement à la lecture analyse le HTML de chaque document servi (AngleSharp), PDF embarqués compris : à surveiller sur les lectures groupées volumineuses.
2. ⚠️ api-mail — `MedicalDocumentHtml` instancie `HtmlBodySanitizer` directement (mappeurs statiques) plutôt que par injection.
3. ⚠️ Le test de téléchargement s'appuie sur `SecurityHeadersIntegrationTests` pour `nosniff` (en-tête global) au lieu de le relire lui-même.
4. ⚠️ mobile — sous iOS (WKWebView), vérifier au plan de test que le cadre sandboxé sans `allow-same-origin` affiche bien le document (vérifié sous Chromium par la voie e2e).
5. ⚠️ weda2 — avertissement de budget : bundle initial 2,01 Mo pour 2 Mo.
6. ⚠️ weda2 — `mss:build:production` échoue sur `apps/mss/src/environments/environment.prod.ts`, jamais versionné (dette existante, hors task).

### Échecs hors task (constatés au `/review`, non bloquants)

- `EmailReadingUseCaseTests.FilterTodayEmailsShouldReturnOnlyTodayAsyncAsync`, `ImapFolderServiceIntegrationTests.GetFolderTodayAsync_…`, `GetFolderNotSeenTodayAsync_…` : rouges **entre minuit local et minuit UTC** seulement (rejoués à 00 h 38, heure locale 22 h 38 UTC) ; verts sur le même commit à 23 h 38 ; fichiers et services non touchés par la task. Bug de fuseau horaire existant → task à ouvrir.
- `SeededThreadsAreCountableTests.SeveralDistinctThreadSizesReachTheCounter` : flaky connu (déjà suivi), vert au rejeu.

## Timings

*(généré par `tools/timing/report.sh --task task-368 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 17 s | — | — | — | — |
| /develop | ok | 50 min 02 s | 9 (1 min 22 s) | 16 (10 min 50 s) | — | interop-cda 2B/3T, api-mail 5B/11T, client-angular 1B/2T, client-mobile 1B/0T |
| /sonar | ok | 8 min 00 s | 1 (21 s) | 5 (5 min 54 s) | 2 (39 s) | 1 itération(s), api-mail 1B/5T |
| /lint-angular | ok | 3 min 16 s | 1 (24 s) | 1 (53 s) | — | 1 itération(s), client-angular 1B/1T |
| /lint-mobile | ok | 12 s | — | — | — | 0 erreur au départ |
| /e2e | ok | 52 min 28 s | — | — | — | e2e ×5 (18 min 44 s) |
| /review | ok | 8 min 23 s | 4 (23 s) | 4 (4 min 47 s) | — | api-mail 1B/1T, client-mobile 1B/1T, client-angular 1B/1T, interop-cda 1B/1T |
| /tech-writer | ok | 42 s | — | — | — | — |
| **Total cycle** | | **2 h 03 min** | **15 (2 min 32 s)** | **26 (22 min 26 s)** | **2 (39 s)** | |

Autres commandes mesurées : lint ×3 (58 s), nuget-wait ×1 (3 min 06 s), restore ×2 (48 s)
