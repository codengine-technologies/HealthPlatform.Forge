# todo-task-154.md — Opposition patient : garde-fou serveur à l'envoi + acquittement mobile

**Repos**: dtos-mss, api-mail, client-blazor, client-angular, client-mobile
**Dependencies**: —
**Epic**: E012

## Objective

Faire porter par le **backend** la règle « opposition patient à l'envoi », aujourd'hui
purement cliente, et aligner le **mobile** sur l'acquittement explicite déjà en place
sur les deux clients web.

Constat (suite au test humain de task-138) :

- `api-mail` n'applique **aucun** contrôle d'opposition à l'envoi : `POST /sendmail`
  passe directement à `SendMailAsync`. L'opposition n'existe côté serveur que comme
  donnée CRUD (`PatientsController`). Un appel API direct, ou un client défaillant,
  envoie à un patient opposé sans obstacle.
- `client-blazor` (`NewMailComponent`) et `client-angular` (`mail-compose`) affichent
  un **confirm bloquant** avant envoi (« Souhaitez-vous continuer l'envoi ? »).
- `client-mobile` (task-138) n'affiche qu'un **bandeau passif** : le geste d'envoi
  n'est jamais interrompu.

### Règles métier (arbitrées)

1. **L'opposition n'est pas un blocage dur** : le PS peut passer outre après
   acquittement explicite — c'est le comportement produit existant sur les deux
   clients web, on le généralise. (À la différence de l'INS non qualifiée, qui
   reste un blocage absolu.)
2. **Le serveur devient le porteur de la règle** (defense in depth) : pour chaque
   destinataire patient MES (`…@patient.mssante.fr`, INS dérivable de l'adresse),
   si `oppositionMssPatient` est active et que le client n'a **pas** posé le champ
   d'acquittement, l'envoi est **refusé** — erreur `409 Conflict` en
   `application/problem+json` (RFC 7807, règle 12 : exception typée
   `ConflictException`, jamais d'INS/trait dans le `detail`).
3. **Champ de contrat** : `MailDto.OppositionAcknowledged` (booléen, défaut
   `false`). Posé à `true` par le client uniquement après confirmation explicite
   du PS dans la dialog d'opposition.
4. **Périmètre serveur** : destinataires patients MES uniquement.
   `oppositionMssProfessionnel` reste un garde-fou **client** — pour un
   destinataire PS, le serveur n'a pas de contexte patient fiable permettant de
   décider. Justifié, hors scope serveur.
5. **Fiche patient inconnue ou sans opposition enregistrée** → l'envoi passe
   (pas d'opposition connue = pas de refus).
6. **Tous les chemins d'envoi** sont couverts par la garde : envoi direct,
   file d'attente offline (pending actions), annuler-et-remplacer.
7. **Trace PGSSI-S** : un envoi effectué malgré opposition (acquitté) est
   journalisé côté serveur comme événement dédié, corrélé `traceId`, sans INS
   ni trait en clair (clé hashée comme l'existant).
8. **Frontends** :
   - Blazor et Angular : le confirm existant pose désormais
     `OppositionAcknowledged = true` quand le PS choisit « Continuer ».
   - Mobile : ajout d'une **dialog de confirmation pré-envoi** (annulable,
     parité web — même pattern que la dialog de confirmation d'identité INS
     de task-138) ; « Continuer » pose le flag. Le bandeau passif existant
     est conservé (information au fil de la saisie).
9. **Déploiement en lockstep** (règle 11 — US-complete) : dès que le serveur
   applique la règle, tout client qui n'envoie pas le flag verra ses envois
   vers patients opposés refusés. Les 4 repos livrent donc dans la même US ;
   la validation humaine se fait sur l'ensemble assemblé.

## Definition of Done

- [ ] Build passe sur tous les repos listés (0 erreur) ; tests 0 échec
- [ ] `dtos-mss` : champ `OppositionAcknowledged` ajouté à `MailDto`, package NuGet publié, consommateurs bumpés
- [ ] `api-mail` : envoi vers patient MES avec `oppositionMssPatient` active **sans** acquittement → `409` ProblemDetails (title explicite, aucun INS/trait dans `detail`)
- [ ] `api-mail` : même envoi **avec** acquittement → envoi effectué + événement PGSSI-S journalisé (sans INS en clair)
- [ ] `api-mail` : envoi sans opposition (ou fiche inconnue) → comportement inchangé
- [ ] `api-mail` : garde effective sur les 3 chemins (direct, file offline, annuler-et-remplacer) — couverts par les tests
- [ ] Tests unitaires backend : ≥ 1 test par branche de la garde (opposé sans flag, opposé avec flag, non opposé, fiche inconnue, destinataire non patient)
- [ ] Test d'intégration endpoint `sendmail` : 409 opposition + happy path acquitté (règle 1b)
- [ ] `client-blazor` : « Continuer » du confirm opposition pose le flag ; test unitaire ; libellés via Localizer
- [ ] `client-angular` : « Continuer » du confirm opposition pose le flag ; test unitaire ; libellés FR en dur (pas de ngx-translate côté MSS)
- [ ] `client-mobile` : dialog de confirmation pré-envoi en cas d'opposition (annulable) ; « Continuer » pose le flag ; bandeau conservé ; tests unitaires (confirmer → envoi avec flag, annuler → pas d'envoi) ; libellés FR en dur ; `data-testid` sur la dialog et ses boutons
- [ ] Aucune donnée de santé (INS, NIR, traits) en clair dans les logs client et serveur, ni dans le ProblemDetails

## Manual Test Plan

- Lancer le backend : `cd Api/Mail && dotnet run`
- Poser une opposition MES sur un patient de test (page Patient du client Blazor,
  section consentement/opposition — ou `PUT /api/v1/patients/{ins}/opposition`)
- **Blazor** (`cd Client/Blazor && dotnet run`) : nouveau message vers l'adresse MES
  du patient → dialog opposition → **Annuler** : rien ne part ; recommencer →
  **Continuer** : l'envoi aboutit
- **Angular** (`cd Client/Angular/front && npm start`) : même scénario
- **Mobile** (`cd Client/Mobile && npm start`) : compose vers le patient opposé →
  bandeau visible pendant la saisie ; à l'envoi, **dialog de confirmation** →
  Annuler : rien ne part ; Continuer : l'envoi aboutit
- **API directe** : rejouer `POST /sendmail` vers le même destinataire avec
  `oppositionAcknowledged` absent/`false` (Postman/curl) → `409` en
  `application/problem+json`, sans INS dans le corps
- Vérifier dans les logs serveur l'événement « envoi malgré opposition (acquitté) »
  corrélé au `traceId`, sans INS en clair
- Retirer l'opposition du patient → l'envoi repasse sans dialog ni 409

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR nouvelle — durcissement d'une exigence déjà portée côté clients (respect du choix patient à l'envoi MSSanté citoyenne)
- **Exigences DSR honorées** : respect de l'opposition patient aux échanges vers Mon Espace Santé, désormais opposable côté serveur (defense in depth) ; parité mobile/web sur l'acquittement
- **INS** : INS dérivée de l'adresse patient MES pour la résolution d'opposition ; INS jamais en log/URL/ProblemDetails — clé hashée côté persistance (existant)
- **Authentification PS** : session e-CPS/PSC existante — l'envoi MSSanté reste sous authentification forte ; l'acquittement est imputable au PS authentifié
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — pas de nouveau format d'échange (un champ booléen ajouté au contrat d'envoi interne)
- **Tracé PGSSI-S** : nouvel événement « envoi malgré opposition patient — acquitté par le PS » (traceId, boîte émettrice, horodatage, clé patient hashée) ; refus 409 tracés par le canal d'erreurs existant ; conservation alignée sur la journalisation d'envoi existante
- **Consentement patient** : cœur de la US — l'opposition du patient devient opposable techniquement, son contournement exige une décision explicite et tracée du PS
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — backend existant
- **AIPD / impact RGPD** : inchangé — aucune donnée nouvelle collectée ; la trace d'acquittement renforce l'imputabilité (registre inchangé)
