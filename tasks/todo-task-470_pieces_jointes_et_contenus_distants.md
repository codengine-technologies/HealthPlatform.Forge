# todo-task-470.md — Pièces jointes et contenus distants : rien ne s'exécute, rien ne se charge à l'insu du médecin

**Repos**: api-mail, client-angular, client-mobile
**Dependencies**: aucune
**Epic**: E025
**Priorité**: EPIC E025, issue de l'audit du 2026-11-12/13, validée par l'humain le 2026-11-13.

> **Origine.** Audit en lecture seule du 2026-11-12/13 (agents « sécurité Angular », « sécurité mobile », « entrées et
> injections »). Le PDF sans type forcé et l'allocation pilotée par la taille déclarée ont été relus dans le code par
> l'orchestrateur le 2026-11-13. Deux audits indépendants ont relevé le contournement du blocage des images distantes.

## Ce qui est établi

Lecture du code au 2026-11-13 :

- **PDF d'un document médical sans type forcé (web).**
  `libs/mss/src/features/mail/components/mail-body/mail-body.component.ts:542-546` (`loadPdf`) et
  `mail-read-only-view/mail-read-only-view.component.ts:257-284` (`ensurePdfLoaded`) créent l'URL `blob:` avec le
  type rendu par le serveur, puis l'affichent dans une `iframe` sans `sandbox`
  (`mail-body.component.html:115`). `previewBlob(blob, 'pdf')` (`core/utils/attachment-preview.util.ts`, task-368)
  n'est appliqué que par `medical-document-modal` et `mail-detail`.
- **Le serveur rend le type déclaré, et cherche par nom.** `ImapService.cs:3721-3722` reprend
  `mimePart.ContentType.MimeType` ; `MailController.cs:844` le sert tel quel (`File(…, attachment.ContentType, …)`).
  La pièce est cherchée par son nom (`MailRepository.cs:3124-3138`, tri sur un Guid) et le nom du PDF généré est
  prévisible (`PdfFileNameGenerator`) : un expéditeur peut joindre une pièce `text/html` homonyme. L'exploitation
  n'est pas reproduite ; le défaut client est certain.
- **Taille déclarée → allocation.** `EmailAddressHelper.cs:133-137` (`EstimateAttachmentSize`) rend le paramètre
  `size` du `Content-Disposition` quand il existe ; `OutgoingMailService.cs:149` en fait la capacité d'un
  `MemoryStream`. Une pièce de 1 Ko déclarée `size=2000000000`, transférée par le médecin, alloue 2 Go avant tout
  contrôle : la réplique tombe, avec tous les médecins qu'elle sert.
- **Assainisseur serveur par liste noire.** `HtmlBodySanitizer.cs` : seuls `javascript:`, `vbscript:` et `data:` sont
  refusés (`:278-300`) ; un attribut d'URL hors liste blanche est gardé (`background`, `:235-240`) ; `style` est gardé
  sauf six jetons (`url(http…)` et `position:fixed` passent, `:53-56`, `:302-311`) ; le mode document médical procède
  par liste noire et ne traite pas `srcdoc` (`:118-123`, `:189-215`). `IsDetached` remonte tous les parents pour
  chaque élément (`:90-94`, `:250-262`) : coût quadratique sur un HTML très imbriqué, sans borne de profondeur, à
  chaque lecture.
- **Blocage des contenus distants contournable (clients).** Mobile `core/utils/remote-content.util.ts:16` et `:24`
  (`/^\s*(?:https?:)?\/\//i`), web `libs/mss/src/core/utils/remote-content.util.ts:18` : décision sur le texte. Une
  URL `https:\\hôte\p.gif` (le navigateur lit `\` comme `/`), une URL relative, un `<base href>` ou un `srcdoc`
  échappent au blocage ; l'image se charge à l'ouverture.
- **Liens d'un mail (mobile).** `mail-body.component.html:88` rend le corps sans intercepter les clics. L'origine de
  l'application est `https://app.weda.fr` (`capacitor.config.ts:15`) : un lien vers cette origine recharge
  l'application sur une route interne (dont `/authentication?code=…`) ; tout autre schéma part en intention Android.
- **Assistant IA.** Web : `core/utils/ai-markdown.util.ts:31-37` neutralise `html` et `image`, pas `link` ; un lien
  d'hameçonnage produit par une injection dans un mail est cliquable, sans domaine visible. Mobile :
  `features/mail/components/ai-chat/ai-chat.component.ts:412-417` ouvre `${scheme}:${value}` (`tel:`, `sms:`) sans
  valider le numéro ; `:327-345` pré-remplit des destinataires proposés par le modèle.
- **Export CSV du journal d'audit (web).** `features/audit/mss-audit.component.ts:291-296` (`escapeCsv`) ne traite que
  `;`, `"` et le saut de ligne ; l'objet d'un mail reçu (`:261`) commençant par `=` est évalué par le tableur.

## Objective

Une pièce jointe ou un contenu venu d'un mail ne s'exécute jamais dans l'application, ne charge aucune ressource
distante sans le geste du médecin, et ne peut pas faire tomber le serveur.

Règles :

1. **Type des pièces jointes.**
   - Le serveur sert en `application/octet-stream` tout type hors d'une liste blanche (PDF, images matricielles, texte
     brut), avec `Content-Security-Policy: sandbox` sur toute réponse de téléchargement.
   - Les clients forcent le type de tout aperçu (`previewBlob`, web ; équivalent mobile).
   - Le PDF d'un document médical est désigné par son identifiant de pièce, jamais par son nom.
2. **Taille.** Aucun tampon n'est dimensionné sur une taille déclarée par l'expéditeur. La copie est plafonnée à la
   taille maximale de pièce jointe et refusée au-delà (400 `ProblemDetails`).
3. **Assainisseur serveur par liste blanche.**
   - Schémas : `http`, `https`, `mailto`, `cid` ; `data:image/*` sur `img` seulement.
   - CSS : propriétés en liste blanche, sans `url()` ni `position`.
   - Attributs d'URL hors liste retirés ; `srcdoc` retiré, dans le corps comme dans le mode document médical.
   - Profondeur d'imbrication (512) et taille de corps bornées ; au-delà, le contenu est rendu en texte.
4. **Blocage des contenus distants (clients).** Toute décision se prend sur l'URL analysée (`new URL(valeur, base)` :
   protocole et hôte), jamais sur le texte ; une URL relative est traitée comme distante ; `base` et `srcdoc` sont
   retirés. « Afficher les images » reste le seul moyen de charger une ressource distante.
5. **Liens d'un mail (mobile).** Seuls `https:` et `mailto:` s'ouvrent, hors de la WebView, après affichage de l'hôte ;
   un lien vers l'origine de l'application n'est jamais suivi.
6. **Assistant IA.**
   - Web : un lien est rendu avec son domaine visible, et s'ouvre dans un nouvel onglet isolé
     (`rel="noopener noreferrer"`).
   - Mobile : un numéro est validé (forme téléphonique) et affiché avant ouverture ; les destinataires d'une action
     sont pris dans le carnet ou l'Annuaire et confirmés à l'écran.
7. **Export CSV.** Une cellule qui commence par `=`, `+`, `-`, `@`, une tabulation ou un retour chariot est
   neutralisée (préfixe apostrophe) et mise entre guillemets.

### Hors périmètre

- La regex sans délai de `CDAHtmlTransformer` (`interop-cda`) : plausible, à qualifier par un test avant d'ouvrir une
  task sur ce dépôt.
- Le XSS de rédaction et les contenus stockés (brouillons, modèles, signatures) : task-469.

## Definition of Done

- [ ] Tests unitaires : liste blanche des types servis ; assainisseur (schémas, CSS, attributs d'URL, `srcdoc`,
      profondeur) ; estimation de taille sans paramètre déclaré.
- [ ] **Test d'intégration de bout en bout (règle 1b)** : un CDA avec PDF et une pièce `text/html` homonyme du PDF ;
      `GET` de la pièce HTML rend `application/octet-stream` et l'en-tête `Content-Security-Policy: sandbox` ; le PDF
      du document, demandé par son identifiant, rend `application/pdf`. Vu rouge.
- [ ] **Test d'intégration du transfert** : transférer un mail dont la pièce de 1 Ko déclare `size=2000000000` réussit
      (pièce intacte) ; une pièce réellement au-delà du plafond est refusée en 400 `ProblemDetails`. Vu rouge (par
      mutation : capacité rétablie sur la taille déclarée).
- [ ] **Test d'intégration de l'assainisseur** : un corps porteur de `background=`, `style="background:url(…)"`,
      `position:fixed`, `srcdoc` et d'un lien `intent:` est relu par `GET …/emails/content/{uid}` sans eux ; un HTML
      imbriqué 100 000 fois est servi en texte, dans un temps borné. Vu rouge.
- [ ] **Deux personnes sur la même boîte** (règle 14) : le délégataire télécharge une pièce ; la trace
      `AttachmentDownload` porte le délégataire (RPPS, nom, rôle).
- [ ] Tests de composant web et mobile, vus rouges par mutation : aperçu PDF forcé en `application/pdf` (web, deux
      sites) ; blocage de `https:\\…`, d'une URL relative, de `base` et de `srcdoc` ; liens d'un mail filtrés et
      confirmés (mobile) ; lien de l'IA avec domaine visible (web) ; numéro validé (mobile) ; cellule CSV neutralisée.
- [ ] **Scénarios e2e** ajoutés à `Api/Mail/e2e/scenarios.yml`, mobile et angular requis :
      - `E2E-DETAIL-007` v1 : « un mail aux images distantes, même déguisées, ne charge rien avant « Afficher les
        images » » ;
      - `E2E-ATTACH-002` v1 : « le PDF d'un document médical s'affiche ; une pièce HTML déguisée ne s'exécute pas ».
- [ ] Trou du filet : `E2E-DETAIL-007` et `E2E-ATTACH-002` prouvés rouges sur le code non corrigé, lignes ajoutées dans
      `conventions/e2e.md`.
- [ ] Prévention (règle d'or) :
      - `conventions/csharp.md` : « liste blanche, jamais liste noire, pour tout contenu servi » ; « jamais de capacité
        ou de tampon tirés d'une taille déclarée par un tiers » ;
      - `conventions/angular.md` : « décider sur `new URL()`, jamais sur une regex de texte » ; « tout aperçu de blob a
        un type forcé ».
- [ ] Aucune donnée de santé dans les logs ; `data-testid` sur chaque élément interactif ajouté.
- [ ] Build et tests verts : `HealthPlatform.Api.Mail.sln`, weda2 (`nx build weda2`, `nx test weda2`,
      `nx test mss-lib`), client-mobile (`npm run build`, `npm test -- --watch=false --browsers=ChromeHeadless`).
- [ ] client-angular : code-only, aucun commit.

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail/src/AppHost && dotnet run`), weda2 (`cd Client/Angular/front && npm start`) et le
   mobile (`cd Client/Mobile && npm start`).
2. Injecter un CDA avec PDF, accompagné d'une pièce `text/html` portant le même nom que le PDF généré et un script.
   Web : ouvrir le mail ; le PDF s'affiche, rien ne s'exécute.
3. Injecter un mail aux images distantes déguisées (`https:\\…`, URL relative, `background=`, `url()` dans un style).
   Web et mobile, onglet réseau ouvert : aucune requête externe avant « Afficher les images ».
4. Mobile : dans un mail, toucher un lien `tel:` puis un lien vers `https://app.weda.fr/…` : le premier demande
   confirmation après validation du numéro, le second n'est pas suivi.
5. Transférer un mail dont une pièce déclare une taille de 2 Go : le transfert aboutit, l'API reste stable.
6. Web : exporter le journal d'audit contenant un mail d'objet `=HYPERLINK("https://exemple";"Ouvrir")` ; l'ouvrir
   dans un tableur : la cellule est du texte.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — sécurité transverse de la lecture des messages
- **Vague Ségur** : hors Ségur — correctif de sécurité
- **Exigences DSR honorées** : non applicable — exigences PGSSI-S (intégrité, confidentialité, disponibilité)
- **INS** : non applicable — aucune identité patient manipulée
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel
- **Habilitations** : personnes de la boîte sous verdict de l'opérateur (règle 14), inchangé
- **Interop CI-SIS** : CDA R2 avec PDF embarqué (`nonXMLBody` ou pièce externe) : désignation du PDF par identifiant ;
  lecture inchangée
- **Tracé PGSSI-S** : inchangé — téléchargement et export déjà tracés au nom de la personne
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — base de la boîte
- **AIPD / impact RGPD** : inchangée — la lecture d'un message n'est plus révélée à l'expéditeur à l'insu du médecin
