# todo-task-469.md — Rédaction sans script : citations, brouillons, modèles, signatures

**Repos**: api-mail, client-mobile, client-angular
**Dependencies**: aucune
**Epic**: E025
**Priorité**: EPIC E025, issue de l'audit du 2026-11-12/13, validée par l'humain le 2026-11-13. Faille la plus grave
du client mobile : un script dans la WebView lit le jeton et pilote l'API, envoi compris.

> **Origine.** Audit en lecture seule du 2026-11-12/13 (agents « sécurité mobile », « entrées et injections »,
> « bugs mobile »). Chaîne relue dans le code par l'orchestrateur le 2026-11-13.
>
> **client-angular** n'est listé que pour le scénario e2e : l'éditeur web (tiptap) n'exécute pas de script, la
> rédaction web n'est pas modifiée par cette US.

## Ce qui est établi

Lecture du code au 2026-11-13 :

- **Citation mobile non échappée.** `features/mail/components/mail-compose/mail-compose.component.ts:1666-1669`
  (`buildQuote`) interpole `from.name || from.address` et le corps dans du HTML. Le corps vient de
  `content.bodyHtml || content.body` (`:468`) : un mail sans partie HTML fournit son texte brut, que le serveur
  n'assainit pas (`ImapService.cs:3516-3517` n'assainit que `BodyHtml`), pas plus que le nom de l'expéditeur.
- **Éditeur mobile.** `features/mail/components/html-editor/html-editor.component.ts:33-48` écrit la valeur reçue dans
  `el.innerHTML`, hors de l'assainisseur d'Angular ; `replaceRange` (`:95-100`) insère le retour de la correction
  orthographique par un `<template>` sans assainissement. La signature est injectée par le même chemin (`:535`, `:555`).
- **Analyse du corps dans une `div` détachée.** `core/utils/compose-body.util.ts:16` et `:34` font
  `holder.innerHTML = html` sur un élément créé par `document.createElement` : un `<img onerror>` s'y exécute. Appelé
  par l'enregistrement automatique (toutes les 30 s).
- **Serveur : contenus stockés bruts.** `DraftService.cs:405` et `:434` (`BodyHtml = payload.BodyHtml`), brouillons
  rangés par boîte ; `MailTemplateController.cs:108` et `:137` (`Body = dto.Body`), modèles rangés par boîte ;
  `SignatureController.cs:96` et `:130` (`HtmlContent = dto.HtmlContent`). Seuls les envois en attente sont assainis
  à la lecture (`MailController.cs:1643`). `SignatureController` et `MailTemplateController` ne contrôlent pas
  `ModelState` alors que le 400 automatique est désactivé : `[Required]` et `[MaxLength]` sont inopérants,
  `HtmlContent` n'a pas de taille maximale.
- **Aucune CSP mobile.** `src/index.html` n'a pas de `Content-Security-Policy` ; `capacitor.config.ts:24` active
  `CapacitorHttp`, qui lève le CORS pour tout appel du script.
- **Courses dans la rédaction mobile.** `loadDraft` (`mail-compose.component.ts:561-591`) et `loadSignatures`
  (`:521-542`) ne sont pas gardés par `composeSession` : la réponse tardive d'un brouillon A remplace la rédaction du
  brouillon B (destinataires, objet, corps, pièces, identifiant) ; une signature tardive s'injecte dans un brouillon
  rouvert. `favoritesLoaded` (`:808-827`) n'est jamais remis à zéro et le composant n'est pas dans
  `mailbox-scoped-states.ts` : après une bascule, « À » propose les favoris du carnet de la boîte précédente.

## Objective

Aucun contenu venu d'un mail reçu ou d'une autre personne de la boîte ne peut exécuter de script dans la rédaction ;
la rédaction mobile n'applique jamais une réponse qui ne lui appartient plus.

Règles :

1. **Citation** (Répondre, Répondre à tous, Transférer) : le nom de l'expéditeur et un corps en texte brut sont
   échappés ; seul un corps HTML assaini par le serveur est cité comme HTML.
2. **Éditeur mobile** : tout HTML qui entre dans l'éditeur est assaini (valeur reçue, signature, correction
   orthographique). Toute analyse d'un corps se fait dans un document inerte, jamais dans un élément du document de
   l'application.
3. **Serveur** : brouillons, modèles et signatures passent par l'assainisseur HTML **à l'écriture et à la lecture**.
   La lecture couvre les données déjà stockées : aucune reprise n'est nécessaire. Leur saisie est contrôlée (champs
   requis, taille maximale) et un refus sort en 400 `ProblemDetails`.
4. **CSP mobile** : aucun script en ligne ni `eval` ; `object-src 'none'` ; `base-uri 'none'` ; `connect-src` limité
   aux hôtes de l'API et du proxy d'authentification de l'environnement. Les images restent permises : leur blocage
   relève de task-470.
5. **Rédaction mobile** : une réponse (brouillon, signature) qui n'appartient plus à la rédaction ouverte est ignorée ;
   les favoris appartiennent à la boîte ouverte et sont vidés à la bascule.

### Hors périmètre

- Le blocage des images distantes, les liens d'un mail, les pièces jointes : task-470.
- La rédaction web (fiabilité de l'envoi, enregistrement en quittant l'écran) : task-475.

## Definition of Done

- [ ] Tests unitaires : citation d'un expéditeur nommé `<img src=x onerror=…>` et d'un corps texte porteur de balises
      (échappés) ; citation d'un corps HTML assaini (gardé) ; assainissement serveur d'un brouillon, d'un modèle et
      d'une signature.
- [ ] **Test d'intégration de bout en bout (règle 1b)** : un brouillon, un modèle et une signature enregistrés avec
      `onerror` et `<script>` sont relus sans eux par `GET` de chaque ressource ; une donnée piégée déjà stockée
      (insérée directement dans le stockage) est relue assainie. Cas d'échec : une signature au-delà de la taille
      maximale ou sans nom rend 400 en `ProblemDetails`. Vu rouge.
- [ ] **Deux personnes sur la même boîte** (règle 14) : le délégataire enregistre un brouillon piégé ; le titulaire
      le relit assaini ; la trace d'audit de l'enregistrement porte le délégataire (RPPS, nom, rôle).
- [ ] Tests de composant mobile, vus rouges par mutation : citation échappée ; éditeur assaini (valeur, signature,
      correction) ; analyse du corps sans exécution ; brouillon et signature tardifs ignorés ; favoris vidés à la
      bascule.
- [ ] CSP mobile en place pour chaque environnement de build ; l'application démarre, se connecte et envoie sous CSP
      (vérifié par la voie e2e mobile).
- [ ] **Scénario e2e** `E2E-COMPOSE-007` v1 ajouté à `Api/Mail/e2e/scenarios.yml`, mobile et angular requis :
      « répondre à un message dont l'expéditeur et le corps portent du HTML actif n'exécute rien, et la citation montre
      le texte ». Le seed du banc porte ce message.
- [ ] Trou du filet : scénario `E2E-COMPOSE-007` prouvé rouge sur le mobile non corrigé, ligne ajoutée dans
      `conventions/e2e.md`.
- [ ] Prévention (règle d'or) :
      - `conventions/angular.md` : « jamais d'`innerHTML` sur une valeur non assainie ; jamais d'analyse HTML dans un
        élément créé par `document.createElement` » ;
      - `conventions/csharp.md` : « tout HTML stocké pour être resservi passe par `IHtmlBodySanitizer`, à l'écriture et
        à la lecture ».
- [ ] Aucune donnée de santé dans les logs ; `data-testid` sur chaque élément interactif ajouté.
- [ ] Build et tests verts : `HealthPlatform.Api.Mail.sln`, client-mobile (`npm run build`,
      `npm test -- --watch=false --browsers=ChromeHeadless`), weda2 (`nx test mss-lib` pour le scénario).
- [ ] client-angular : code-only, aucun commit.

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail/src/AppHost && dotnet run`), le mobile (`cd Client/Mobile && npm start`) et weda2
   (`cd Client/Angular/front && npm start`).
2. Envoyer à la boîte de test un mail **texte** dont le nom d'expéditeur et le corps portent
   `<img src=x onerror=alert(1)>`.
3. Mobile : ouvrir le mail, toucher Répondre, puis Transférer. Aucune alerte ; la citation montre le texte tel quel.
4. Web : enregistrer un modèle et une signature contenant `<img src=x onerror=alert(2)>`. Mobile : les insérer dans une
   rédaction. Aucune alerte.
5. Mobile : ouvrir un brouillon A sur réseau lent (outils du navigateur), fermer, ouvrir un brouillon B : la rédaction
   reste celle de B.
6. Mobile : basculer vers une autre boîte, ouvrir une rédaction : « À » ne propose que les favoris de la nouvelle boîte.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — sécurité transverse du poste de rédaction
- **Vague Ségur** : hors Ségur — correctif de sécurité
- **Exigences DSR honorées** : non applicable — exigence PGSSI-S (intégrité, confidentialité du poste de travail)
- **INS** : non applicable — aucune identité patient manipulée
- **Authentification PS** : inchangée — PSC (e-CPS), eIDAS substantiel ; l'US protège le jeton de session du
  détournement par un script
- **Habilitations** : personnes de la boîte sous verdict de l'opérateur (règle 14) ; brouillons et modèles à la boîte,
  signatures à la personne (inchangé)
- **Interop CI-SIS** : non applicable — aucun échange modifié
- **Tracé PGSSI-S** : inchangé — enregistrement d'un brouillon, d'un modèle, d'une signature imputé à la personne
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — base et cache de la boîte
- **AIPD / impact RGPD** : inchangée — réduction d'un risque de compromission
