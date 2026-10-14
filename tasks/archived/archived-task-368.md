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

- [ ] Build et tests verts : weda2 (`npm run build`, `npm test`), api-mail, interop-cda
- [ ] Tests unitaires rouges d'abord, client-angular :
  - [ ] une pièce `text/html`, `text/xml` ou `application/xhtml+xml` n'est jamais rendue en `iframe` ; une pièce `text/plain` l'est en `text/plain`
  - [ ] toute `iframe` de rendu (aperçu, `medical-html-frame`) porte `sandbox` sans `allow-scripts` ni `allow-same-origin`
  - [ ] aucune occurrence de `bypassSecurityTrustHtml` sur un contenu reçu ou généré (test d'architecture par recherche dans les sources)
  - [ ] le blocage du contenu distant traite `url(&quot;…&quot;)`, `image-set()` et les attributs `style` des CDA
- [ ] Test d'intégration de bout en bout pour `GET /api/v1/mail/folders/{folder}/emails/{uid}/download/attachment/{name}` : une pièce `text/html` est servie avec `Content-Disposition: attachment` et `X-Content-Type-Options: nosniff`, lus dans la réponse réelle, vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout pour la lecture d'un mail portant un CDA dont la partie narrative contient `<td onmouseover=…>` : le `bodyHtml` du document médical renvoyé ne contient plus aucun attribut `on*`, vu rouge (règle 1b)
- [ ] interop-cda : test de transformation — un attribut `onmouseover` d'un `<td>` narratif n'est plus recopié dans le HTML ; `style` et `colspan` le restent
- [ ] Scénario E2E-SECURITY-001 « un contenu reçu piégé ne s'exécute pas » ajouté dans `Api/Mail/e2e/scenarios.yml` (clients : angular `requis`, mobile selon l'arbitrage), implémenté dans weda2 : mail seedé avec une pièce HTML et un CDA piégés, aucune exécution constatée
- [ ] Trou du filet : scénario prouvé rouge sur le code d'avant, ligne ajoutée dans `conventions/e2e.md`
- [ ] Aucune donnée de santé en clair dans les logs ajoutés
- [ ] client-angular : modifications non commitées (code-only), liste des fichiers dans le `## Develop log`

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
- `Api/Mail` (pushed) : fix/task-368-contenu-recu-cloisonne — https://github.com/codengine-technologies/HealthPlatform.Api.Mail/tree/fix/task-368-contenu-recu-cloisonne
- `Client/Mobile` (pushed) : fix/task-368-contenu-recu-cloisonne — https://github.com/codengine-technologies/HealthPlatform.Mobile/tree/fix/task-368-contenu-recu-cloisonne
- `interop/interop.cda.parser` (pushed) : fix/task-368-contenu-recu-cloisonne — https://github.com/codengine-technologies/interop.cda.parser/tree/fix/task-368-contenu-recu-cloisonne
- `client-angular` (code-only) : branche courante `feature/nova-rewriting-mss-weda-integration` (instantané au `/start`) — humain gère commit, push, PR TFS
- `dtos-mss` (paresseuse) : aucune branche

## Develop log

> **Reprise (2026-10-14)** — l'humain a annulé le code client-angular de la première passe et repris la
> task en développement. Décision au `/start` : « Refaire weda2 seul ». Les commits backend et mobile,
> déjà validés par la chaîne complète du premier passage, sont **réutilisés tels quels** (cherry-pick
> sur les branches recréées) ; seule la partie weda2 est refaite, test d'abord.

### Commits réutilisés (repos poussés)

| Repo | Commit | Contenu |
|---|---|---|
| interop-cda | `ddf83c1` | XSL : la partie narrative ne recopie plus que les attributs autorisés (plus de `on*`, ni de `javascript:`) — Interop.Cda.Parser 109.0.0 publié |
| api-mail | `46d3ce02` | bump Interop.Cda.Parser 109.0.0 |
| api-mail | `a7d6f427` | `HtmlBodySanitizer.SanitizeMedicalDocument` appliqué à la lecture (`MedicalDocumentHtml`, null préservé), seed `mail-piege` + cellule piégée du CDA sans INS, catalogue E2E-SECURITY-001 v1 |
| client-mobile | `646ffbd` | cadre sandboxé, contenu distant bloqué (DOM), fenêtre du document par le cadre, PDF retypés, aperçu de la chronologie bloqué, IA sans bypass, spec E2E-SECURITY-001 |

### client-angular — refait test d'abord (code-only, non commité)

| Bloc | Rouge vu | Vert |
|---|---|---|
| 1. Aperçu des pièces (ANG-01) — `attachment-preview.util` : PDF / images hors SVG / `text/plain` seulement, blob retypé | module absent ; 5 rouges mail-attachment + mail-detail (`text/html`, `text/xml`, xhtml, svg rendus ; type servi gardé) | 82 |
| 2. Contenu distant sur le DOM (ANG-38) — `remote-content.util` réécrit (template / DOMParser) | 7 rouges : `url(&quot;…&quot;)`, `image-set()`, sans guillemets, sans schéma, srcset, poster, `<style>`, `@import`, CDA complet | 42 |
| 3. `medical-html-frame` (ANG-02, ANG-39) — `sandbox="allow-popups allow-popups-to-escape-sandbox"`, PDF embarqués sortis du cadre, bannière « Afficher les images » portée par le cadre | 4 rouges (sandbox, PDF sortis, blocage + affichage, re-blocage) ; mail-body : 2 rouges (bannière en double) | 11 |
| 4. Fenêtre du document patient (ANG-03) — rendue par le cadre, PDF retypé `application/pdf` | 2 rouges (HTML en `innerHTML`, type `text/html` gardé) | 2 |
| 5. Sorties d'IA (ANG-04) — `ai-markdown.util` (HTML brut échappé, images en texte), 3 composants sans `bypassSecurityTrustHtml`, `[innerHTML]` simple | module absent ; garde d'architecture rouge sur les 3 composants (le modal, déjà corrigé, n'y figurait plus) | 7 |
| 6. Chronologie du patient (ANG-39, parité mobile) — aperçu sans ressource distante | 1 rouge (`img` distante gardée par l'assainisseur Angular) | 1 |
| 7. Vue en lecture seule — le commentaire « iframe sandboxée » devient vrai, prouvé par un test | — | 3 |

**Preuves de mutation** (restaurées depuis copie, jamais `git checkout`) :
- `ai-markdown.util.ts` : renderers `html` / `image` retirés → 4 tests d'échappement + garde rouges.
- `medical-html-frame.component.ts` : attribut `sandbox` retiré → 3 rouges (frame, lecture seule, modal).

**Fichiers modifiés** (`git status`, Client/Angular) :
- utils : `ai-markdown.util.ts` (+spec), `attachment-preview.util.ts` (+spec), `remote-content.util.ts` (+spec)
- mail : `ai-chat-panel.component.ts`, `mail-attachment.component.ts` (+spec), `mail-body.component.{ts,html,scss}` (+spec), `mail-detail.component.{ts,html}` (+spec), `mail-read-only-view.component.html` (+spec), `mail-summary.component.ts`, `medical-html-frame.component.ts` (+spec)
- patient : `medical-document-modal.component.{ts,html,scss}` (+spec), `timeline-document-group.component.{ts,html}` (+spec)
- ui : `mail-summary.component.ts`
- e2e : `specs/functional.e2e.ts` (E2E-SECURITY-001 + sélecteurs `iframe.medical-html-frame__iframe`), `specs/live-ai.e2e.ts` (sélecteur)

### Validation

- weda2 : `npm run build` ✓ ; `npm test` ✓ — 11 projets, 2 700 tests (14 skipped, préexistants), 0 échec ; libs/mss 823/823.
- `tsc --noEmit` lib + e2e ✓ ; eslint 0 erreur sur les fichiers touchés.
- Passe qualité §Q : relecture du diff weda2, aucun nettoyage à appliquer.

### Règle 1b — comportements atteignables par un endpoint (api-mail)

| Comportement | Test d'intégration | Preuve rouge |
|---|---|---|
| La lecture d'un mail sert le `bodyHtml` du document médical sans `on*`, mise en forme gardée | `FolderOperationsEndToEndTests.ReadingAMail_ServesItsMedicalDocumentHtml_FreeOfActiveContent_AndKeepsItsLayout` | mutation 2026-10-14 : `MedicalDocumentHtml.Sanitize => html` → `Assert.DoesNotContain() Failure: Sub-string found` ; restauré, vert (6/6 avec le téléchargement) |
| Une pièce `text/html` est servie `Content-Disposition: attachment` + `X-Content-Type-Options: nosniff` | `MailAttachmentDownloadIntegrationTests` | non-régression : comportement déjà en place sur `develop`, verrouillé par le test (pas de comportement modifié) |

### Limite documentée

- Pas de trace côté Weda (décision humaine du 2026-10-13).

## Sonar log

Mode A (chaîné), branche `fix/task-368-contenu-recu-cloisonne`, serveur 9.9.8 (`sonar.login`). Les
conteneurs étaient arrêtés (Exited 255) : redémarrés (`sonarqube_db` puis `sonarqube`), UP sur 9000.

Analyse complète : build Release ✓, 5 suites OpenCover vertes (190 + 3 635 + 690 + 1 229 + 884 réussis,
16 ignorés préexistants), `end` EXECUTION SUCCESS, traitement serveur SUCCESS.

- **Phase 1 (new code)** : 0 issue, Quality Gate OK — rien à corriger.
- **Phase 2 (legacy)** : 0 bug, 0 vulnérabilité, 0 code smell — rien à corriger. 0 itération.

### KPIs qualité (baseline → final)

La baseline est l'analyse du premier passage de la task, sur le même contenu (commits réutilisés par
cherry-pick) : Quality Gate OK, 0 issue.

| Métrique | Baseline | Final | Δ |
|---|---|---|---|
| Quality Gate (new code) | OK | OK | = |
| New coverage | — | 96,8 % | — |
| New bugs / vulnérabilités / smells | 0 / 0 / 0 | 0 / 0 / 0 | = |
| New duplication | — | 0,11 % | — |
| Bugs / Vulnérabilités / Smells | 0 / 0 / 0 | 0 / 0 / 0 | = |
| Coverage projet | — | 97,9 % | — |
| Duplication projet | — | 0,4 % | — |
| Ratings (fiabilité / sécurité / maintenabilité) | A / A / A | A / A / A | = |
| Security hotspots | 0 | 0 | = |

## Lint log

Mode A, `client-angular` (code-only, aucune opération git). Portée `tag:scope:mss` (3 projets), sur
l'arbre de travail non commité (`nx run-many --projects=tag:scope:mss`, cache désactivé : un
`affected --head=HEAD` ne verrait pas des modifications non commitées).

- Baseline : **0 erreur**, 95 avertissements (JSDoc `@example` sans description, préexistants).
- 0 itération : rien à corriger. Build et tests de `/develop` toujours valables (aucune modification depuis).

## Lint mobile log

Mode A, branche `fix/task-368-contenu-recu-cloisonne` (commit `646ffbd` réutilisé). Baseline `npm run lint` : **All files pass linting** — 0 erreur, 0 itération, aucun commit.

## E2E log

| Voie | Commande | Résultat |
|---|---|---|
| angular | `npm run e2e:mss` | ✅ 38 verts, 1 flaky (E2E-COMPOSE-002, en quarantaine humaine — task-350), 0 rouge, parité verte |
| mobile | `npm run e2e:headless` | ✅ 35 verts, 0 flaky, 0 rouge, parité verte |
| porte | `mss.mail.e2e.dll gate --report mobile=… --report angular=…` | sortie 0 |

Démontage vérifié : aucun conteneur e2e résiduel, ports libres.

**Trou du filet (DOD)** — E2E-SECURITY-001 rejoué seul, sans retry, sur le weda2 d’avant la task (22 fichiers de `libs/mss` remis à leur version `HEAD` depuis copie, restaurés à l’octet près ensuite, tests re-verts) : **rouge** — `page.waitForEvent: Timeout 15000ms exceeded while waiting for event "download"` (la pièce HTML piégée est ouverte en aperçu au lieu d’être téléchargée). Le backend porte déjà l’assainissement à la lecture : la cellule du CDA est couverte côté serveur (preuve 1b du `## Develop log`) ; la preuve du cadre sans `sandbox` est portée par les tests unitaires et la mutation du `## Develop log`. Ligne `conventions/e2e.md` (trou du filet task-368) déjà présente.

**E2E : vert** — aucun parcours rouge hors quarantaine, parité verte.

**En quarantaine (posée par l'humain, non bloquant)** (1) :

- [angular] « rédaction — corriger l’orthographe, appliquer, envoyer : le texte corrigé arrive, la citation intacte » (E2E-COMPOSE-002) — Flaky — correction : task-350

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
| E2E-COMPOSE-002 | 1 | headless | Faire corriger l'orthographe de son texte, appliquer la correction, puis envoyer | ⚠️ flaky | ✅ |
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

- `interop-cda` : https://github.com/codengine-technologies/interop.cda.parser/pull/12 — label `awaiting-human-merge`
- `api-mail` : https://github.com/codengine-technologies/HealthPlatform.Api.Mail/pull/295 — label `awaiting-human-merge` (après le merge d'interop : consomme Interop.Cda.Parser 109.0.0, déjà publié)
- `client-mobile` : https://github.com/codengine-technologies/HealthPlatform.Mobile/pull/93 — label `awaiting-human-merge`
- `client-angular` : code-only — humain gère commit/push TFS et ouverture PR. Branche `feature/nova-rewriting-mss-weda-integration`. Liste des fichiers modifiés ci-dessous :
  - `front/e2e/mss-e2e/specs/functional.e2e.ts`
  - `front/e2e/mss-e2e/specs/live-ai.e2e.ts`
  - `front/libs/mss/src/core/utils/ai-markdown.util.spec.ts`
  - `front/libs/mss/src/core/utils/ai-markdown.util.ts`
  - `front/libs/mss/src/core/utils/attachment-preview.util.spec.ts`
  - `front/libs/mss/src/core/utils/attachment-preview.util.ts`
  - `front/libs/mss/src/core/utils/remote-content.util.spec.ts`
  - `front/libs/mss/src/core/utils/remote-content.util.ts`
  - `front/libs/mss/src/features/mail/components/ai-chat-panel/ai-chat-panel.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-attachment/mail-attachment.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-attachment/mail-attachment.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-body/mail-body.component.html`
  - `front/libs/mss/src/features/mail/components/mail-body/mail-body.component.scss`
  - `front/libs/mss/src/features/mail/components/mail-body/mail-body.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-body/mail-body.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.html`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-detail/mail-detail.component.ts`
  - `front/libs/mss/src/features/mail/components/mail-read-only-view/mail-read-only-view.component.html`
  - `front/libs/mss/src/features/mail/components/mail-read-only-view/mail-read-only-view.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/mail-summary/mail-summary.component.ts`
  - `front/libs/mss/src/features/mail/components/medical-html-frame/medical-html-frame.component.spec.ts`
  - `front/libs/mss/src/features/mail/components/medical-html-frame/medical-html-frame.component.ts`
  - `front/libs/mss/src/features/patient/components/medical-document-modal/medical-document-modal.component.html`
  - `front/libs/mss/src/features/patient/components/medical-document-modal/medical-document-modal.component.scss`
  - `front/libs/mss/src/features/patient/components/medical-document-modal/medical-document-modal.component.spec.ts`
  - `front/libs/mss/src/features/patient/components/medical-document-modal/medical-document-modal.component.ts`
  - `front/libs/mss/src/features/patient/components/timeline-document-group/timeline-document-group.component.html`
  - `front/libs/mss/src/features/patient/components/timeline-document-group/timeline-document-group.component.spec.ts`
  - `front/libs/mss/src/features/patient/components/timeline-document-group/timeline-document-group.component.ts`
  - `front/libs/mss/src/ui/mail-summary/mail-summary.component.ts`
- `devops`, `psc-proxy-*` : managed manually by the human (non concernés)

## Code Review Summary

**APPROVED** — 0 bloquant, 2 suggestions, corrigées ensuite à la demande de l'humain (voir « Suite de la revue »).

Validation : interop-cda build ✓ / 503 tests ✓ ; api-mail build ✓ / 6 628 tests ✓ (16 ignorés préexistants) ; client-mobile build ✓ / 1 049 tests ✓ ; weda2 build ✓ / 11 projets ✓. Toutes les branches à jour de `develop`. DOD vérifiée ligne à ligne (CSP retirée par décision humaine). `## E2E log` vert.

| Comportement (règle 1b) | Test d'intégration | Preuve rouge |
|---|---|---|
| Un CDA reçu (Dovecot → enrichissement) est stocké et servi sans contenu actif | `FolderOperationsEndToEndTests.ReceivingACdaWithActiveContent_StoresAndServesItsHtmlFreeOfIt_AndKeepsItsText` | rouge avant (stocké brut) ; mutation M1 → rouge |
| Pièce `text/html` servie `Content-Disposition: attachment` (`nosniff` : `SecurityHeadersIntegrationTests`) | `MailAttachmentDownloadIntegrationTests.DownloadAttachment_OfAnHtmlPart_IsServedAsAnAttachmentToSave` | mutation `/review` 2026-10-14 : `File(content, type)` sans nom → `Expected "attachment", Actual null` ; restauré, vert |

Suggestions (non bloquantes) :
- api-mail : assainir à l'écriture plutôt qu'à chaque lecture (re-parse par lecture ; migration des documents anciens à prévoir).
- api-mail : `MedicalDocumentHtml` instancie `HtmlBodySanitizer` en statique (Infrastructure → classe concrète d'Application) plutôt que par injection.

### Suite de la revue (2026-10-14) — les deux suggestions corrigées

Demande de l'humain : « corrige directement ces deux findings sur la branche en cours ». Commit api-mail `a577a900`
sur `fix/task-368-contenu-recu-cloisonne` (PR #295) :

- `CdaParsingService` reçoit `IHtmlBodySanitizer` par injection et assainit le HTML juste après la transformation
  XSL : stocké et servi assaini, plus de re-parse à la lecture. Les lectures servent le HTML stocké ;
  `MedicalDocumentHtml` est supprimé.
- Migration `20261014120000_SanitizeStoredMedicalDocumentHtml` : documents stockés avant le correctif assainis une
  fois, par pages de 100 (clé `Id`), réécrits seulement s'ils changent, assainisseur injecté (enregistré dans le
  conteneur du coureur), journal de comptes seulement. Pas de descente.
- Test d'écriture : le test qui seedait du HTML brut après les migrations est remplacé par une ingestion réelle
  (XDM déposé dans Dovecot, cellule portant une CSS active que la XSL 109 garde) ; il lit la valeur stockée et la
  réponse de l'endpoint. Rouge avant (`background:url('javascript:parent.steal()')` stocké), vert après.
- Mutations (restaurées depuis copie) : M1 assainissement retiré de `CdaParsingService` → test d'ingestion rouge ;
  M2 migration arrêtée après la première page → test de migration rouge.
- api-mail complet vert : domain 190, infrastructure 690, api 1 229, application 3 635, intégration 885 (+16 ignorés).
- **Migration retirée** (commit `9a0f6752`, décision humaine du 2026-10-14) : la base est réinitialisée au
  déploiement, aucun document stocké avant l'assainissement à l'écriture ne subsiste. La migration, son test (et la
  preuve M2) et l'enregistrement de l'assainisseur dans le conteneur du coureur sont supprimés ; intégration
  884/884 verte (+16 ignorés).

## Timings

*(généré par `tools/timing/report.sh --task task-368 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | ok | 10 s | — | — | — | — |
| /develop | ok | 17 min 49 s | 10 (1 min 48 s) | 20 (12 min 24 s) | — | interop-cda 2B/3T, api-mail 5B/13T, client-angular 2B/4T, client-mobile 1B/0T, reprise : weda2 refait test d'abord, backend/mobile réutilisés |
| /sonar | ok | 8 min 49 s | 2 (1 min 07 s) | 10 (12 min 20 s) | 4 (1 min 22 s) | api-mail 2B/10T, QG OK, 0 issue |
| /lint-angular | ok | 18 s | 1 (24 s) | 1 (53 s) | — | client-angular 1B/1T, 0 erreur au départ |
| /lint-mobile | ok | 38 s | — | — | — | 0 erreur au départ |
| /e2e | ok | 14 min 42 s | — | — | — | e2e ×8 (31 min 06 s), 2 voies vertes, porte 0, preuve rouge weda2 |
| /review | ok | 7 min 34 s | 8 (48 s) | 9 (9 min 08 s) | — | api-mail 2B/3T, client-mobile 2B/2T, client-angular 2B/2T, interop-cda 2B/2T, APPROVED, 3 PRs |
| /tech-writer | ok | 19 s | — | — | — | — |
| **Total cycle** | | **50 min 22 s** | **21 (4 min 08 s)** | **40 (34 min 46 s)** | **4 (1 min 22 s)** | |

Autres commandes mesurées : lint ×5 (1 min 40 s), nuget-wait ×1 (3 min 06 s), restore ×2 (48 s)

## Merged

Validé manuellement par l'humain (`/merge task-368 --i-tested`, 2026-10-14). Squash-merge sur `develop`, dans l'ordre :

| Repo | PR | Commit squash |
|---|---|---|
| interop-cda | #12 | `638a6516b76181d47c95aa9d7bbd2d1532f4f70a` |
| api-mail | #295 | `bf3d104daf41515bb48ce89b0aa8f9da7fb2147f` |
| client-mobile | #93 | `fd2d1a90bca874bf6af50c3a5f8c75a4e008ae8a` |

- La PR api-mail #295 porte aussi, à la demande de l'humain, le correctif de `SEQ_URL` dans l'AppHost (port Seq 5341 partagé avec l'endpoint ; les logs d'api-mail n'arrivaient plus dans Seq).
- Branches `fix/task-368-contenu-recu-cloisonne` supprimées (distantes et locales) ; clones revenus sur `develop`.
- `client-angular` : code-only, commit / push / PR TFS par l'humain. Les deux correctifs d'affichage faits après la revue (hauteur du cadre, alignement à gauche du CDA) sont dans le même arbre de travail.
- Aucune branche de staging à nettoyer.
