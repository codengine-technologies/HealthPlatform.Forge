# Audit de détection de bugs — `client-angular` / weda2, module messagerie (2026-10-13)

> **Périmètre** : le module messagerie (`libs/mss`, ~35 000 lignes) et ce qui l'entoure dans weda2 : authentification (`apps/weda2/src/lib/auth`, `features/authentication`), embarquement dans Weda (`apps/weda2/src/lib/embedded`), intercepteurs, `app.config.ts`, environnements, manifestes `Client/Angular/devops` quand un défaut en dépend. Les autres modules de weda2 (agenda, comptabilité, antécédents, DMP, prescription) et le design system sont hors périmètre.
> **Version auditée** : branche `feature/nova-rewriting-mss-weda-integration` @ `84c2e6ac` (arbre propre, travail de task-340 inclus).
> **Méthode** : analyse statique, en lecture seule, découpée en 7 zones (authentification et session, embarquement Weda, cœur MSS — état, API et temps réel —, écran mail — liste, dossiers, recherche —, lecture et rendu de contenu non fiable, rédaction et envoi, patients — contacts, audit, paramètres). Chaque constat a été tracé dans le code (appelants et appelés), contrats confirmés côté api-mail. Les constats marqués **✔** ont en outre été **contre-vérifiés** ligne à ligne pendant la consolidation.
> **Ce que l'audit n'est pas** : aucun code n'a été exécuté, aucun test ajouté. Un constat « Probable » repose sur une hypothèse explicitée. Les défauts déjà suivis sont exclus : empilement des sessions IMAP au rechargement de l'iframe, fermeture au `pagehide` et surveillance de la session partagée (task-365) ; filtre « type d'action » sans effet de l'écran d'audit (défaut serveur `PostgresAuditReader`).
> **Suite prévue** : création des tasks dans un second temps — une proposition de regroupement figure en fin de document.

---

## 1. Synthèse

**≈ 100 constats bruts**, **78 après dédoublonnage** (les mineurs voisins sont regroupés par ligne) (plusieurs zones ont trouvé indépendamment les mêmes défauts — signalé en « origine »).

| Sévérité | Nombre | Dont contre-vérifiés ✔ |
|---|---|---|
| 🔴 Critique | 21 | 14 |
| 🟠 Majeur | 41 | — |
| 🟡 Mineur | 16 lignes (≈ 30 défauts) | — |

**Trois causes racines** portent l'essentiel des constats critiques :

1. **Aucun cloisonnement d'origine pour le contenu reçu.** Pièces jointes, documents CDA et sorties d'IA sont rendus dans l'origine de weda2 (blob de même origine, `iframe` sans `sandbox`, `bypassSecurityTrust*`), sans CSP `script-src`. Un émetteur MSSanté quelconque peut exécuter du script avec les droits du médecin.
2. **Des réponses périmées appliquées à l'écran courant.** Contenu d'un mail, synthèse IA, liste d'un dossier, préparation d'import : aucune annulation (`switchMap`) ni garde « est-ce encore l'élément affiché ? ». Le praticien voit — et agit sur — le mail, le dossier ou le patient précédent.
3. **L'identité « boîte » et « dossier » n'est pas figée.** Les en-têtes de boîte sont lus au moment de l'envoi de la requête, les messages ne sont identifiés que par leur UID (propre à chaque dossier), et le contrat `switching` / `generation` de `MailboxSessionStore` n'a aucun consommateur. Une action part sur le mauvais message, dans le mauvais dossier ou la mauvaise boîte.

**Les dix à traiter d'abord**, par ordre de priorité proposé :

1. **ANG-01 ✔ / ANG-02 ✔ / ANG-03 ✔ / ANG-04** — Exécution de script depuis un contenu reçu : pièce jointe HTML prévisualisée, CDA (attributs `on*` recopiés par la XSL), fenêtre du document patient, synthèse IA. Vol de session, lecture et envoi de mails au nom du médecin.
2. **ANG-05 ✔** — `mssApiUrl` n'est pas surchargeable au déploiement : weda2 de production envoie le jeton du praticien à l'api-mail de **dev**.
3. **ANG-08 ✔** — Le contenu, les documents médicaux et les résultats d'un mail s'affichent sous l'en-tête d'un autre : import Weda, acquittement de biologie et lecture CDA pour le mauvais patient.
4. **ANG-20 ✔** — La chronologie patient affiche les documents d'autres patients qui partagent le même mail.
5. **ANG-10 ✔ / ANG-11 ✔** — Après un changement de messagerie : une suppression part sur le mail de même UID de l'autre boîte ; embarqué, l'écran mêle les deux boîtes.
6. **ANG-14 ✔** — « Peut-être parti » affiché comme un échec ordinaire : double envoi d'un courrier médical.
7. **ANG-06 ✔** — Les appels à api-mail ne rafraîchissent jamais le jeton : messagerie en 401 environ 4 min après la connexion, temps réel coupé.
8. **ANG-07 ✔** — La déconnexion pour inactivité ne déconnecte jamais (poste de cabinet partagé).
9. **ANG-15 ✔ / ANG-16 ✔ / ANG-17** — Rédaction : un message sans rapport annule un envoi antérieur ; brouillon jamais créé, contenu perdu à la fermeture ; rédaction remplacée sans sauvegarde.
10. **ANG-18 ✔ / ANG-19** — Pièces jointes perdues sans le dire : homonymes (lecture, transfert, import Weda) et transfert envoyé avant la fin du téléchargement.

---

## 2. Constats critiques 🔴

### Exécution de script depuis un contenu reçu

**ANG-01 ✔ — L'aperçu d'une pièce jointe `text/html` s'exécute dans l'origine weda2** (`mail-detail.component.ts:595-602, 626-640`, `mail-detail.component.html:676-697` — `iframe [src]` sans `sandbox` ; type pris du serveur, donc de l'expéditeur : api-mail `MailController.cs:832`). Un clic sur la ligne de la pièce (geste par défaut) charge un blob `text/html` de même origine. Variantes : `text/xml` avec `<html:script>`, CDA `nonXMLBody` en `text/html` transformé en pièce jointe par `CdaParsingService`. Aucune CSP `script-src` (`nginx.conf` ne pose que `frame-ancestors`). *Confirmé.* *Direction* : ne prévisualiser en `iframe` que PDF et images ; texte forcé en `text/plain` ; `sandbox` sans `allow-scripts` ni `allow-same-origin` ; côté serveur `Content-Disposition: attachment` et `nosniff` ; CSP.

**ANG-02 ✔ — `medical-html-frame` : `iframe` sans `sandbox`, de même origine, qui affiche le HTML CDA non assaini** (`medical-html-frame.component.ts:28-34, 120-128` ; XSL `interop.cda.parser/.../html/style.xsl:419-437` — `<xsl:copy-of select="@*"/>` sur les tableaux ; `CdaParsingService.cs:569-599` — `HtmlBodySanitizer` non appliqué au HTML CDA). Un CDA portant `<td onmouseover="parent.…">` s'exécute au survol de l'onglet affiché par défaut. Même sans faille de l'assainisseur, un corps de mail assaini garde `target` et `rel` : `<a target="_top">` remplace tout l'onglet weda2 (faux écran PSC). Le commentaire « iframe sandboxée » de `mail-read-only-view` est faux. *Confirmé (sink, absence de sandbox, recopie XSL) ; exploit Probable (aucune validation XSD bloquante trouvée).* *Origine : zones 5 et 7.* *Direction* : `sandbox` sur l'`iframe` ; assainir le HTML CDA ; retirer `copy-of @*` et la recopie de `link_html/@*`.

**ANG-03 ✔ — Le HTML CDA est injecté dans le DOM de l'application** (`medical-document-modal.component.ts:95-97` — `bypassSecurityTrustHtml`, `.html:96`). Depuis la chronologie patient, le même CDA piégé s'exécute dans le document principal, et son `<style>` s'applique à toute l'application. *Confirmé (sink) ; exploit Probable (même hypothèse).* *Origine : zones 5 et 7.* *Direction* : rendre via `medical-html-frame` corrigé ; supprimer le contournement.

**ANG-04 — La sortie des modèles d'IA est rendue en HTML brut** (`ai-chat-panel.component.ts:246-249`, `mail-summary.component.ts:113-119`, `ui/mail-summary/mail-summary.component.ts:229-231` — `marked.parse` puis `bypassSecurityTrustHtml` ; aucun DOMPurify). Une injection de prompt dans un mail reçu (« reproduis `<img src=x onerror=…>` ») est recopiée dans la synthèse, persistée en base et affichée sans clic par le widget de notifications. *Probable (hypothèse : le modèle recopie la charge) ; sink confirmé ✔.* *Direction* : retirer le contournement (l'assainisseur Angular s'applique), ou DOMPurify ; désactiver le HTML brut dans `marked`.

### Authentification, session et déploiement

**ANG-05 ✔ — `mssApiUrl` n'est pas surchargeable : toute instance déployée vise l'api-mail de dev** (`environment.prod.ts:17` = `https://mss-api.dev.k8s.office.weda.fr` ; `Client/Angular/devops/k8s/weda2-frontend-configmap.yaml:21-29` ne fournit que `apiEndpoint`, `authEndpoint`, `authClientId`, `wedaRedirectUrl` ; `main.ts:25-39` fait `Object.assign(environment, runtimeConfig)`). Le Bearer Keycloak du praticien part, avec `withCredentials`, vers le cluster de dev. *Probable (hypothèse : cette ConfigMap est celle déployée et rien d'autre n'injecte `mssApiUrl`).* *Direction* : `mssApiUrl` et `embeddedHostOrigins` dans la ConfigMap ; échouer à l'amorçage si une clé obligatoire manque ; retirer les URL de dev de `environment.prod.ts`.

**ANG-06 ✔ — Les appels à api-mail ne déclenchent jamais de rafraîchissement du jeton** (`auth-interceptor.utils.ts:101-111` — `shouldSkipRequest` laisse passer toute URL hors `apiEndpoint`/`authEndpoint` ; `auth.interceptor.ts:59-67` ; `mss-headers.interceptor.ts` pose le jeton sans regarder l'échéance ; `error.interceptor.ts:104-107` tait les 401). Avec un jeton de 120 s et la tolérance api-mail de 2 min, la messagerie tombe en 401 environ 4 min après la connexion ; le flux SSE (jeton en query string) meurt et n'est jamais rouvert. En embarqué, le rechargement d'iframe masque en partie le défaut ; en autonome il est systématique. *Confirmé (mécanisme) ; déconnexion à 30 min Probable.* *Direction* : `MSS_API_URL` origine de confiance de l'intercepteur (rafraîchissement et rejeu sur 401) ; rafraîchissement préventif avant `exp`.

**ANG-07 ✔ — La déconnexion pour inactivité ne déconnecte jamais** (`auto-logout.service.ts:207-240` — `initialize()` n'est appelé nulle part, `authStore` reste `null`, `triggerLogout()` journalise et rend la main ; sortie de veille au-delà de la fenêtre non traitée). Sur un poste de cabinet partagé, la session d'un médecin absent reste ouverte, boîte et dossiers visibles. Le bouton « Se déconnecter » du dialogue ne fait rien. *Confirmé.* *Direction* : injecter le store ; `timeRemaining <= 0` = déconnexion immédiate ; test d'intégration jusqu'à `logout()`.

### Le mauvais mail, le mauvais patient

**ANG-08 ✔ — Le contenu d'un mail s'affiche sous l'en-tête d'un autre** (`mail-detail.component.ts:737-750, 777-806` — un `subscribe` par sélection, sans annulation, `mailContent` jamais vidé ; `:184-341` tous les calculs lisent `mailContent()` ; `mail-detail.component.html:705-740, 922-928`). Pendant chaque chargement — et durablement si A répond après B ou si B échoue — le corps, les onglets CDA, la biologie, le panneau d'acquittement et la section Patient de B montrent les documents de A. Conséquences : acquittement « pris connaissance » d'une valeur critique attribuée au mauvais mail ; import Weda qui présélectionne le patient de A (trouvé par INS, donc présenté comme fiable) et classe le courrier de B dans son dossier (`weda-import.component.ts:258-277, 530-552`). Le garde `originalLoaded` (task-350) ne protège que Répondre et Transférer. *Confirmé (contenu périmé) ; import dans le mauvais dossier Probable (fenêtre de chargement).* *Origine : zones 2 et 5.* *Direction* : `switchMap` sur `(folderPath, uid)`, vider le contenu au changement, ne rendre corps et panneau qu'avec `originalLoaded()` ; côté import, vérifier que `content` appartient à `mail`.

**ANG-21 — La synthèse IA du mail A s'affiche sous l'identité patient du mail B** (`mail-summary.component.ts:48-52, 126-147` — requête non annulée ; `mail-detail.component.ts:165` — `showSummary` non remis à faux). Latence du LLM : fenêtre de plusieurs secondes. *Confirmé.* *Direction* : `switchMap` ou garde `(folderPath, uid)`.

**ANG-09 — Une préparation d'import abandonnée présélectionne le patient du premier message, sans sélection visible** (`weda-import.component.ts:189-194, 258-287, 530-552`). Annuler pendant « Préparation de l'import… », rouvrir sur B : la résolution tardive de A pose `selectedPatientId`, aucun bouton radio n'est coché, « Importer » est actif. *Confirmé (fenêtre étroite).* *Direction* : compteur de génération vérifié après chaque `await` ; remettre la sélection à `null` si le patient n'est plus listé.

**ANG-20 ✔ — La chronologie patient affiche tous les documents de chaque mail, y compris ceux d'autres patients** (`patient-timeline.component.ts:121-129` — `allDocuments` sans filtre sur `doc.patientId` ; api-mail `MailRepository.cs:1253-1334` renvoie tous les documents du mail). Un mail à deux CDA rattachés à X et Y : la fiche de X affiche le document, la biologie et la synthèse clinique de Y. Les décisions « supprimé », « supplanté » et « doublon » sont aussi annulées à l'affichage. *Confirmé.* *Direction* : servir le dossier depuis `ActiveDocumentsForPatient` ; à défaut filtrer sur `doc.patientId`.

**ANG-10 ✔ — Une suppression « annulable » en attente part sur l'autre boîte après un changement de messagerie** (`mail-pending-delete.service.ts:56-78, 102-126` ; `mss-headers.interceptor.ts:44-51` lit `currentEmail()` à l'émission ; `mailbox-switcher.component.ts:140-153`). Glisser vers la Corbeille, changer de boîte dans les 6 s : `deleteEmail('INBOX', uid)` part avec `Client-Email = B`. Un mail de B jamais vu part à la corbeille (définitivement si la source est la corbeille) ; celui de A réapparaît. *Confirmé.* *Origine : zones 3 et 4.* *Direction* : figer la boîte dans le lot à l'`enqueue` ; vider ou valider les opérations différées avant la bascule.

**ANG-11 ✔ — Embarqué, changer de messagerie garde l'écran de l'ancienne boîte, puis y mêle la nouvelle** (`mailbox-switcher.component.ts:152` navigue vers la même URL ; aucun `onSameUrlNavigation` ; `generation()` n'est lu nulle part hors du store ; `MailStateService` absent de `MSS_RESETTABLE_STORES`). Dossiers, liste, mail ouvert et rédaction restent ceux de A sous l'en-tête B ; le rafraîchissement de 30 s ajoute les UID de B. Les gestes par UID partent vers B, une réponse rédigée dans A part de B, le temps réel est coupé. *Confirmé (mode embarqué, praticien multi-boîtes).* *Origine : zones 3 et 4.* *Direction* : recréer la vue sur `generation` ; jeter les réponses de génération périmée ; inscrire l'état mail dans la purge.

**ANG-12 — Vue conversation : glisser, sélectionner ou supprimer une réponse du fil agit sur un message du dossier courant** (`mail-list.component.html:162-175` ; `mail-list.component.ts:860-907, 953-970, 1022-1028` — chemin = `selectedFolder.path`, UID = enfant ; `mail-state.service.ts:739-764` ; le fil inclut Envoyés depuis task-268). Glisser sa réponse envoyée (Envoyés/340) vers Archives déplace INBOX/340, sans rapport. *Confirmé (collision d'UID INBOX/Envoyés très fréquente).* *Direction* : identifier par `(folderPath, uid)` partout ; grouper les actions par `mail.folderPath`.

**ANG-13 — Des réponses en vol non annulées affichent la liste d'un dossier sous le contexte d'un autre** (`mss-mail.component.ts:346-359, 491-566, 735-751` ; `mail-list.component.ts:214-250`). Rafraîchissement de A en vol, clic sur B : l'en-tête et le menu reviennent à A, la liste montre B ; « Supprimer » appelle `bulkDeleteEmails(A.path, UID de B)`. Un nouveau clic sur B ne fait rien (`distinctUntilChanged`). *Probable (cache froid contre cache chaud).* *Direction* : un seul flux `switchMap` ; ne jamais réécrire `selectedFolder` pour un dossier quitté.

### Rédaction et envoi

**ANG-14 ✔ — « Peut-être parti » affiché comme un échec ordinaire : double envoi** (`mail-compose.component.ts:1124-1153` ; `problem-details.utils.ts` ne connaît que `MAIL_SERVER_AUTH_REFUSED` ; `mss-pending-sends.component.ts:62-70, 218-231` ; modèle sans `deliveryUncertain` ; api-mail `GlobalExceptionHandler.cs:132-135` — 503 `MAIL_DELIVERY_UNCERTAIN`, `DraftController.cs:160` — 502). La rédaction affiche « Erreur lors de l'envoi » et réactive le bouton ; les envois en attente affichent « le message reste prêt à partir ». L'avertissement décidé par task-330 n'atteint jamais le praticien web. *Confirmé.* *Origine : zones 3 et 6.* *Direction* : reconnaître le code, afficher le `detail`, bloquer la nouvelle tentative ; `deliveryUncertain` dans le modèle ; statut 0 et 504 = incertain.

**ANG-15 ✔ — Le contexte « annule et remplace » n'est jamais vidé à la réouverture : un message sans rapport annule l'original** (`mail-compose.component.ts:707` — seul `doClose` le vide ; `:1102, :1466` routent sur ce contexte ; api-mail `MailCancellationService.cs:207-218`). « Annuler et remplacer » sur X, puis « Nouveau message » sans fermer : le nouveau message part par `cancel-and-replace` et X est marqué « [ANNULÉ] ». *Confirmé.* *Direction* : vider le contexte dans `openCompose`/`reset`, ou le passer dans le prefill.

**ANG-16 ✔ — L'identifiant de brouillon est posé avant toute création côté serveur** (`mail-compose.component.ts:509-541, 2125-2136, 2160-2195` ; api-mail : PUT sur un id inconnu = 404). Rédaction de moins de 30 s puis clic ailleurs : PUT 404, la rédaction se ferme, **tout est perdu sans message**. Premier autosave en échec : tous les suivants partent en 404, l'envoi échoue à chaque tentative. *Confirmé.* *Direction* : n'adopter l'id qu'après le POST réussi ; garder la rédaction ouverte en cas d'échec ; sur 404 à l'envoi, repasser par `sendmail`.

**ANG-17 — Plusieurs chemins remplacent la rédaction en cours sans l'enregistrer** (`mail-compose.component.ts:479-481, 549-572` ; `mail-folder-list.component.ts:100` ; `mss-mail.component.ts:199, 375-378` ; aucune garde `canDeactivate` ni `beforeunload`). « Nouveau message », clic sur un brouillon de la liste, intention de l'hôte, rechargement : jusqu'à 30 s de texte perdues, tout pour une rédaction récente ou ouverte par une intention. *Confirmé.* *Direction* : un seul chemin « enregistrer puis ouvrir » ; `beforeunload` tant qu'il reste du contenu.

**ANG-18 ✔ — Pièces jointes de même nom : le paramètre `occurrence` n'est jamais transmis** (`mss-api.service.ts:1884-1895` ; api-mail `MailController.cs:742-752`, occurrence absente = 0, AUD-41). Lecture : la seconde pièce n'est jamais consultable. Transfert (`mail-compose.component.ts:1566-1593`) : le confrère reçoit deux fois la première. Import Weda (`weda-import.component.ts:601-613`) : la seconde n'est jamais classée. « Envoyé » et « 2 document(s) importé(s) » s'affichent. *Confirmé.* *Origine : zones 2, 5 et 6.* *Direction* : transmettre le rang ; pour le transfert, passer par référence (`ResolvePartsByReferenceAsync` existe).

**ANG-19 — Transfert : on peut envoyer avant la fin du téléchargement des pièces d'origine** (`mail-compose.component.ts:877-894, 1539-1593` ; le bouton ne regarde que `isSending` et les destinataires). Le message part sans l'IHE_XDM ou le PDF, avec « Message envoyé avec succès ». *Confirmé (fenêtre = latence IMAP).* *Direction* : compter les pièces en attente et désactiver Envoyer, ou transférer par référence.

---

## 3. Constats majeurs 🟠

### Authentification et session

**ANG-22 — Toute erreur pendant ou après un rafraîchissement est traitée comme une perte de session** (`auth.interceptor.ts:122-139` — `catchError` après le `switchMap` de rejeu ; `authentication-callback.service.ts:265-277` — `login()` sur toute erreur ; `store-helpers.utils.ts:314-334`). Un 409 métier ou une coupure Wi-Fi de 2 s déconnecte le médecin et révoque la session du proxy (partagée avec Weda). Des `logout()` non souscrits laissent croire à une déconnexion. *Confirmé.*

**ANG-23 — « Se connecter avec Pro Santé Connect » navigue vers `/login`, une route qui n'existe pas** (`app.config.ts:332-341`, `app.routes.ts`, `mss-mailbox-psc-required.component.ts:51-66` ; `loginPsc()` jamais appelé). Le praticien sans boîte ni jeton PSC ne peut pas rattacher sa messagerie depuis l'écran prévu. *Confirmé.*

**ANG-24 — Aucun garde-fou contre une boucle de redirection callback ↔ proxy** (`authentication-callback.service.ts:249-253`, `authentication-callback.component.ts:130-142`, `authentication-callback.utils.ts:477-507`). Échec persistant de l'échange de code, ou `sessionStorage` bloqué : oscillation sans fin. *Probable.*

### Cœur MSS : état, temps réel, entrée

**ANG-25 — Le flux de notifications suit toujours la boîte par défaut, et il est coupé pour de bon après la première bascule** (`notification-stream.service.ts:35-100` — pas de `?mailbox=` ; `reset()` passe `enabled=false` sans réactivation ; `mail-list` n'appelle jamais `disconnect()`). En embarqué avec une boîte désignée ≠ défaut, les toasts « biologie anormale » de la boîte ouverte n'arrivent jamais. *Confirmé.*

**ANG-26 — Envois en attente : `failedActionsCount` ignoré, confirmation interrompue en quittant la page** (`mss-pending-sends.component.ts:292-330, 400-422` — `takeUntilDestroyed` annule une confirmation en pleine transaction SMTP). *Confirmé (champ) ; Probable (interruption).*

**ANG-27 — Le bandeau « N messages prêts à partir » compte ceux d'une autre boîte** (`mailbox-session.store.ts:181-203, 266-302, 392-399` — statut lu avant `open()`, jamais relu à la bascule). Des courriers en attente de la carte ne partent jamais faute de signal. *Confirmé.*

**ANG-28 — Une erreur de chargement des boîtes envoie vers « PSC requis » ou vers l'onboarding** (`mailbox-session.store.ts:410-438` — tout échec vaut `[]`). Un praticien avec sa carte est invité à se reconnecter ; en embarqué, à rattacher une boîte déjà rattachée (409). *Confirmé ; cas 409 `SESSION_MAILBOX_MISMATCH` après détachement Probable.*

**ANG-29 — « Ré-essayer l'authentification » ne fait rien** (`mss-mailbox-management.component.ts:244-246` ; une boîte `AuthFailing` n'est pas sélectionnable et ne repasse `Active` que sur un login réussi). Seul recours : détacher puis rattacher, sans que rien ne le dise. *Confirmé.*

### Écran mail, liste, dossiers, recherche

**ANG-30 — La sélection survit aux changements de page, de filtre et de recherche** (`mail-list.component.ts:436-462, 619-660, 919-924`). « Tout » puis filtre « Non lus » puis « Supprimer » : les lus masqués partent aussi. Aucun compteur de sélection. *Confirmé.*

**ANG-31 — Puce « Bio à acquitter » : filtre limité à la page, non lié au dossier, et invisible après retour de lecture** (`inbox-biology-ack-chip.component.ts:73-125`, `mail-state.service.ts:280-300`). Des résultats critiques sont masqués alors que le compteur dit qu'ils existent ; l'INBOX peut rester filtrée sans aucun signe. *Confirmé.*

**ANG-32 — `isSearchActive` n'est jamais remis à zéro** (`mail-state.service.ts:354-367`, `mss-mail.component.ts:319-334`, `mail-search.component.ts:504-559`). Pagination disparue (50 premiers messages seulement), recherche effacée qui revient, ancienne recherche affichée en dernier. *Confirmé.*

**ANG-33 — Vue « Mails du patient » : retour forcé à la boîte de réception au bout de 30 s, une seule page, et l'identifiant du patient envoyé comme chemin de dossier** (`mss-mail.component.ts:815-864` — dossier virtuel `__patient__/{id}` ; api-mail 404 `FOLDER_NOT_FOUND`). Faux « dossier supprimé depuis un autre logiciel » ; le handle patient part dans l'URL, les journaux et le SSE (régression de l'esprit de task-184). *Confirmé.*

**ANG-34 — `distinctUntilChanged` sur `folderChanged$` rend un dossier impossible à recharger** (`mss-mail.component.ts:309-318, 576-583`). Après un échec de chargement, recliquer sur le dossier ne fait rien. *Confirmé.*

**ANG-35 — Sans volet de lecture (mise en page par défaut) : « Version précédente » ne fait rien, et le bouton « IA » détourne la prochaine lecture** (`mail-list.component.ts:189-199, 602-611` — seul abonné de `requestSelectByUid$` démonté ; `mss-mail.component.ts:388-393` ignore `req.folderPath`). L'IA résume des messages qui n'ont pas été choisis. *Confirmé.*

**ANG-36 — Suppression différée : un échec serveur est avalé, et un brouillon glissé à la Corbeille n'est jamais supprimé** (`mail-pending-delete.service.ts:119-125` — `error: () => undefined` ; UID synthétiques négatifs des brouillons). *Confirmé.*

**ANG-37 — Pannes rendues comme « rien à signaler » ou comme un chargement sans fin** (`biology-ack-pending-kpi-tile.component.ts:119-137` — erreur = tuile masquée ; `mss-mail.component.ts:243-294` — pas de gestion d'erreur des réglages et dossiers). Des biologies critiques en attente paraissent inexistantes pendant une panne. *Confirmé.*

### Lecture et contenu distant

**ANG-38 — Le blocage des images distantes se contourne** (`remote-content.util.ts:12-17` — regex sur `url(` ; AngleSharp resérialise `"` en `&quot;` ; `image-set()` sans `url()`). Pixel espion : l'expéditeur sait que le médecin a ouvert le mail. *Confirmé.*

**ANG-39 — Contenu distant chargé sans consentement dans les CDA, la vue en lecture seule et le widget patient** (`mail-body.component.html:127`, `mail-read-only-view.component.ts:121-123`, XSL `style.xsl:498-509`). *Confirmé.*

**ANG-40 — Identité d'un mail réduite à son UID** (`mail-detail.component.ts:382, 747`, `mail-summary.component.ts:41-49`, `mail-state.service.ts:471-479`). Dans la vue patient (INBOX et dossiers utilisateur mêlés), Archives/42 après INBOX/42 garde le contenu d'INBOX/42. *Probable.*

**ANG-41 — Vue en lecture seule (doublons, widget patient) : chargements non annulés** (`mail-read-only-view.component.ts:177-255`). Le médecin supprime le mauvais exemplaire sur un aperçu périmé. *Confirmé (dépend du timing).*

### Rédaction et envoi

**ANG-42 — Choisir un modèle écrase tout le corps** (`mail-compose.component.ts:939-953`). Citation et signature disparaissent sans confirmation. *Confirmé.*

**ANG-43 — Changer ou retirer la signature après la première frappe : signature en double, ou sous la citation** (`mail-compose.component.ts:2001-2054` ; tiptap retire les commentaires marqueurs). *Confirmé ; course à la réouverture Probable.*

**ANG-44 — Destinataires : une adresse saisie sans Entrée est ignorée, et les Cc/Cci masqués restent destinataires** (`mail-compose.component.ts:717-726, 786-799, 1428-1430`). Destinataire oublié, ou destinataire invisible à l'écran qui reçoit un message médical. *Confirmé.*

**ANG-45 — Le refus explicite du serveur n'est jamais montré** (`mail-compose.component.ts:859-866, 1139-1153, 1754-1765`). Taille totale dépassée (sélection multiple non additionnée), patient opposé (409), brouillon verrouillé : « Erreur lors de l'envoi du message ». *Confirmé.*

**ANG-46 — Brouillon « annule et remplace » rouvert puis envoyé sans carte : envoyé comme un message ordinaire, original jamais annulé** (`mail-compose.component.ts:1102-1108, 1466-1475, 1631-1639` ; `warning` de la réponse ignoré). *Confirmé.*

### Embarquement Weda

**ANG-47 — Le compte rendu d'un import s'affiche sur le message suivant** (`weda-import.component.ts:442-519`). Le praticien croit B importé et ne l'importe pas ; une erreur est attribuée au mauvais message. *Confirmé.*

**ANG-48 — Message portant les documents de deux patients : le premier trouvé par INS est présélectionné et tout est coché** (`weda-import.component.ts:540-551`, `weda-import.utils.ts:175-180`). Le compte rendu de M. B part dans le dossier de Mme A. *Confirmé.*

**ANG-49 — La trace « Traces MSSanté » écrite par Weda ne correspond pas à ce qui est parti** (`mail-compose.component.ts:902-904, 1354-1364, 1714-1726, 1775-1788` ; Weda `NovaMssSentTraceWriter`). Document retiré tracé comme envoyé ; envoi mis de côté (202) ou en file jamais tracé. Obligation de traçabilité Ségur et MSSanté. *Confirmé.*

### Patients, contacts, audit, paramètres

**ANG-50 — La fiche patient est relue par INS au lieu de son handle** (`mss-patient.component.html:142-143`, `mss-api.service.ts:1241-1243, 1307-1382` ; api-mail `PatientRepository.cs:63-94`). Un matricule à deux fiches : chronologie et opposition de l'autre fiche — le front réintroduit le mélange AUD-34 corrigé par task-331. *Confirmé (mécanisme).* Passe en 🔴 si les deux fiches désignent deux personnes.

**ANG-51 — Synthèse biologie : une seule unité et une seule norme par analyte** (`biology-timeline.component.ts:655-671, 377-385`). Glycémie en g/L et en mmol/L sur la même ligne : unité fausse, tendance fausse. Risque clinique. *Confirmé (mécanisme).*

**ANG-52 — Biologie et synthèse calculées sur les seules pages chargées ; la période automatique masque les résultats anciens** (`patient-timeline.component.ts:97-183`, `biology-timeline.component.ts:217-232, 745-752`). Des valeurs anormales anciennes absentes de la grille et du compteur. *Confirmé.*

**ANG-53 — Opposition MSSanté : un échec d'enregistrement laisse la case cochée sans message** (`patient-card.component.ts:157-180`, `patient-consent.component.ts:97-121`). Le praticien croit l'opposition enregistrée ; les envois vers Mon Espace Santé restent possibles. *Confirmé.*

**ANG-54 — Rattachement manuel : la liste de candidats peut appartenir au document précédent** (`patient-attachment-dialog.component.ts:103-158, 292-307`). « Rattacher » (sans confirmation) rattache B au patient de A. *Probable.* *Origine : zones 6 et 7.*

**ANG-55 — Fenêtre du document : le PDF d'un document peut s'afficher sous le titre d'un autre** (`medical-document-modal.component.ts:104-122, 231-254`). *Probable.*

**ANG-56 — Recherche patient et recherche de contacts : un seul échec HTTP désactive la recherche jusqu'au rechargement** (`patient-search.component.ts:59-77` — `catchError` après `switchMap` ; `mss-contacts.component.ts:1003-1022`). Le praticien conclut que le patient n'existe pas. *Confirmé.*

**ANG-57 — Contacts : enregistrer une fiche supprime ses adresses MSSanté secondaires et écrase les changements concurrents** (`mss-contacts.component.ts:409-464` ; api-mail `ContactRepository.cs:143-246`). *Confirmé.*

**ANG-58 — Annuaire : toutes les adresses e-mail FHIR sont importées comme adresses MSSanté** (`mss-contacts.component.ts:829-858` ; api-mail `FhirBundleParser.cs:270-275, 384-391`). Données de santé envoyées hors de l'espace de confiance. *Probable.*

**ANG-59 — Journal d'audit : un dédoublonnage par UID masque des traces et casse le tri, la pagination et l'export** (`mss-audit.component.ts:129-174, 242-260`). Un journal d'imputabilité qui cache des actions ; l'export CSV ne contient que la page dédoublonnée. *Confirmé.*

**ANG-60 — Journal d'audit : appliquer un filtre perd « Erreurs uniquement » et le tri, et désynchronise la pagination** (`mss-audit.component.ts:75-78`, `audit-list.component.ts:44, 125-129`). *Confirmé.*

**ANG-61 — Journal d'audit : les dates personnalisées sont lues en UTC** (`audit-filter.component.ts:38-41, 96-101`). Aux Antilles, tout le dernier jour est exclu de l'extrait. *Confirmé.*

**ANG-62 — Paramètres : un échec de chargement fait réécrire les valeurs par défaut, et un échec d'enregistrement arrête l'enregistrement automatique** (`mss-settings.component.ts:120, 389-410, 460-482`). Alertes « biologie anormale » coupées sans le savoir. *Confirmé.*

---

## 4. Constats mineurs 🟡

| # | Constat | Fichiers | Statut |
|---|---|---|---|
| ANG-63 | « Envoyer » depuis le dossier Weda n'aboutit à rien, sans message, quand l'intégration n'est pas disponible | `compose-intent.provider.ts:36-48`, `weda-integration.service.ts:173-188` | Probable |
| ANG-64 | Import en échec ou hors délai : « Réessayez » crée des doublons dans le dossier (import Weda non transactionnel) | `weda-import.utils.ts:37-47` ; Weda `NovaMssController.PostDocuments` | Probable |
| ANG-65 | Toute page d'un sous-domaine `*.weda.fr` est un hôte de confiance du pont (origines et `frame-ancestors` trop larges) | `environment.prod.ts:11`, `nginx.conf` | Probable |
| ANG-66 | Retour d'erreur OAuth (annulation PSC) : spinner infini | `authentication-callback.component.ts:147-153` | Confirmé |
| ANG-67 | Le créneau de rafraîchissement partagé est libéré au désabonnement d'un appelant : rafraîchissements concurrents | `refresh-token-shared.service.ts:64-82` | Probable |
| ANG-68 | `errorInterceptor` ajoute un toast générique, contradictoire, aux 403/503 métier d'api-mail | `error.interceptor.ts:88-118` | Confirmé |
| ANG-69 | Rechargement inutile sur changement d'identité au callback : page demandée perdue, aller-retour d'authentification | `store-helpers.utils.ts:160-168` | Confirmé |
| ANG-70 | `withDevtools` branché en production (état des stores exposé à l'extension Redux) | `environment.prod.ts:16` | Confirmé |
| ANG-71 | Identité du praticien : le repli sur `preferred_username` ne s'applique jamais (`??` après `join`) | `app.config.ts:269-276` | Confirmé |
| ANG-72 | Accusé de lecture : dossier « envoyés » reconnu par `includes('sent')`, pas par le type SPECIAL-USE (origine : zones 3 et 5) | `core/utils/read-receipt.util.ts` | Probable |
| ANG-73 | `mail-body` remet à zéro l'onglet et « Afficher les images » à chaque changement d'entrée | `mail-body.component.ts:61-74` | Confirmé |
| ANG-74 | Compteurs de non-lus décrémentés deux fois ; minuteurs de compte à rebours qui s'accumulent ; dépliage d'un fil qui affiche les enfants d'un autre ; étiquette lue ailleurs qui reste ; renommage du dossier ouvert qui déclenche « supprimé depuis un autre logiciel » | `mail-list`, `mail-state.service`, `mail-folder-item`, `mss-mail.component`, `mail-folder-list` | Confirmé |
| ANG-75 | Rédaction : autosave non relancé après un échec ; contact sans adresse principale non ajouté, pas de validation de syntaxe ; modèles et signatures (création en double, réponse IA qui écrase, échecs silencieux) ; aperçu de correction d'un message précédent ; dialogue « Nettoyer les doublons » qui garde son acquittement d'une ouverture à l'autre | `mail-compose`, `mss-templates`, `mss-signatures`, `duplicate-cleanup-dialog` | Confirmé |
| ANG-76 | Gestion des comptes : détacher, rattacher ou définir par défaut ignorent l'échec (un détachement échoué peut déconnecter) ; rattachement « déjà rattachée » ou « PSC requise » affiché comme identifiants refusés | `mss-mailbox-management.component.ts`, `mailbox-accounts.service.ts:191-209` | Confirmé / Probable |
| ANG-77 | Cycle de vie de la session : `open()` sans fermeture ni purge, bascules non sérialisées, statut de connexion jamais relu | `mailbox-session.store.ts` | Probable / Confirmé |
| ANG-78 | Journal d'audit : l'aperçu peut afficher le mail ou la frise d'une autre trace ; recherche patient qui promet « nom, prénom, INS » mais ne cherche que le nom | `mss-audit.component.ts:186-311`, `patient-search.component.html:205` | Probable / Confirmé |

---

## 5. Proposition de regroupement en tasks (pour le second temps)

| Task proposée | Constats | Priorité | Repos |
|---|---|---|---|
| **Cloisonner le contenu reçu** : `sandbox` sur toutes les `iframe`, aperçu limité à PDF/image/texte brut, plus aucun `bypassSecurityTrustHtml` sur un contenu reçu ou généré, assainissement du HTML CDA, XSL sans `copy-of @*`, CSP `script-src` | ANG-01, 02, 03, 04, 38, 39 | **0** | client-angular, api-mail, interop-cda |
| **Configuration de déploiement de weda2** : `mssApiUrl` et `embeddedHostOrigins` dans la ConfigMap, amorçage qui échoue sur une clé manquante, `frame-ancestors` restreint, `withDevtools` hors prod | ANG-05, 65, 70 | **0** (vérifier d'abord ce qui tourne) | client-angular, devops |
| **Rafraîchissement du jeton et déconnexion** : api-mail origine de confiance, rafraîchissement préventif, SSE rouvert, perte de session seulement sur refus explicite, inactivité réellement appliquée, PSC sign-in, boucles et spinner du callback | ANG-06, 07, 22, 23, 24, 66, 67, 69, 71 | 1 | client-angular |
| **Le mail affiché est celui qui est sélectionné** : annulation et garde `(folderPath, uid)` sur le contenu, la synthèse IA, la vue en lecture seule, la fenêtre du document et le PDF ; identité `(folderPath, uid)` partout | ANG-08, 21, 40, 41, 55, 73 | 1 | client-angular |
| **Import Weda et identito-vigilance** : génération des préparations, présélection seulement si toutes les identités concordent, compte rendu rattaché au message, `occurrence`, trace des envois exacte, messages d'erreur | ANG-09, 47, 48, 49, 63, 64 (+ 18 côté import) | 1 | client-angular, Weda |
| **Dossier patient fiable** : documents filtrés sur le patient, fiche relue par handle, biologie par unité et non paginée, opposition qui reflète le serveur, rattachement manuel annulable | ANG-20, 50, 51, 52, 53, 54 | 1 | client-angular, api-mail |
| **Changement de messagerie sans fuite** : opérations différées figées sur leur boîte, vue recréée sur `generation`, flux SSE par boîte et rouverts, compteurs relus | ANG-10, 11, 25, 27, 77 | 1 | client-angular |
| **Actions groupées sur les bons messages** : identité `(folderPath, uid)` dans la liste et le fil, un seul flux de chargement des dossiers, sélection vidée aux changements de vue, `distinctUntilChanged` corrigé | ANG-12, 13, 30, 34, 36, 74 | 1 | client-angular |
| **Rédaction : jamais de perte ni de double envoi** : remise incertaine reconnue (rédaction et envois en attente), contexte annule-et-remplace, brouillon créé avant d'être adopté, enregistrement avant remplacement et `beforeunload`, pièces jointes par référence et attente du téléchargement, refus serveur affichés | ANG-14, 15, 16, 17, 18, 19, 26, 42–46, 75 | 1 | client-angular, api-mail |
| **Liste, recherche et puce biologie cohérentes** : recherche remise à zéro, puce bio servie par le serveur, vue patient avec sa propre source paginée (sans handle dans le chemin), version précédente et IA sans volet de lecture, pannes visibles | ANG-31, 32, 33, 35, 37 | 2 | client-angular, api-mail |
| **Entrée et gestion des messageries** : erreur ≠ zéro boîte, « Ré-essayer l'authentification » réel, échecs affichés | ANG-28, 29, 76 | 2 | client-angular, api-mail |
| **Contacts et annuaire** : liste complète des adresses, contrôle de version, adresses MSSanté seulement | ANG-56, 57, 58 | 2 | client-angular, api-mail |
| **Journal d'audit et paramètres** : pas de dédoublonnage, filtres fusionnés, dates locales, export serveur ; réglages non écrasés sur échec | ANG-59, 60, 61, 62, 78 | 2 | client-angular |
| **Messages d'erreur et petits défauts** | ANG-68, 72 | 3 | client-angular |

---

## 6. Couverture — zones examinées et jugées saines

- **Pont avec Weda (`EmbeddedHostService`)** : émission restreinte à `hostOrigin` (jamais `'*'`), réception filtrée sur `event.source` et `event.origin`, schéma validé, `requestId` non devinable, délais par type ; inactif hors iframe. `readComposeIntent` : validation stricte, pas de pollution de prototype ; intention consommée une seule fois. URL construites avec `encodeURIComponent` ; aucune URL signée ne transite par weda2. INS ni affichée ni journalisée dans le panneau Weda.
- **Jetons** : en mémoire uniquement ; `sessionStorage` ne garde que le state OAuth et `last_authenticated_sub`. Bearer jamais envoyé à un tiers ; `debugInterceptor` exclu du build de production ; state OAuth aléatoire, comparé puis supprimé ; ordre de déconnexion de task-285 respecté.
- **Envoi** : verrou synchrone contre le double clic et Ctrl+Entrée ; le brouillon porte pièces jointes, accusé de lecture, blocage de réponse patient, acquittement d'opposition et annule-et-remplace (AUD-06 côté Angular sain) ; aucun envoi hors ligne sans confirmation par carte ; « Répondre à tous » n'inclut ni sa propre adresse ni le Cci ; garde task-350 présente.
- **Rendu** : `HtmlBodySanitizer` (api-mail) correct sur le corps des mails ; PDF embarqués forcés en `application/pdf` ; blobs révoqués ; accusé de lecture jamais envoyé sans geste ; acquittement biologique instancié par document, double clic neutralisé.
- **Liste** : pierres tombales, réconciliation task-353, flux de rafraîchissement (`exhaustMap`), effets à signaux sans boucle, matrice de glisser-déposer, historique de recherche stocké côté serveur.
- **Patients et audit** : détachement manuel confirmé et protégé par `expectedCurrentPatientId` ; INS hors des URL (task-184) ; aucune donnée de santé dans le stockage du navigateur ni la console ; enum `AuditActionType` aligné (0 à 41) ; journal cloisonné par boîte.
