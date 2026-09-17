# todo-task-320.md — Sans Pro Santé Connect, la messagerie est en lecture seule, et le serveur le garantit

**Repos**: api-mail
**Dependencies**: —
**Epic**: E016
**Single frontend**: true

> Remédiation n°3 de l'audit sécurité du registre du 2026-09-16 (écart élevé).
> Voir aussi task-318 (jeton PSC vérifié et lié au compte) et task-319
> (re-validation continue).

## Objectif

Le produit promet, depuis task-304 : *« Hors ligne, le médecin lit ses messages.
[…] Écrire, répondre ou classer sont visiblement désactivés. »* Cette promesse
n'est tenue que par les **écrans**. Côté serveur, une session qui ne porte qu'un
jeton Keycloak — donc **sans carte CPS ni e-CPS** — est acceptée pour marquer lu,
déplacer, supprimer, et surtout **envoyer un message MSSanté** : l'ordre est mis
en file d'attente avec un `202 Accepted`, puis **rejoué automatiquement** dès qu'un
jeton PSC réapparaît, sous l'identité du professionnel.

Autrement dit, quiconque tient une session Keycloak seule peut rédiger des
messages qui partiront **au nom du praticien**, avec sa signature MSSanté, la
prochaine fois qu'il présentera sa carte. C'est contraire au garde-fou non
négociable du PO (*« envoi MSSanté : exiger PSC ou e-CPS, pas un simple mot de
passe »*) et à la PGSSI-S sur l'imputabilité des actes.

Après cette US, **le serveur refuse toute écriture sans session Pro Santé Connect
valide**, et le refus est lisible par les fronts. La lecture des données déjà
synchronisées reste servie, comme aujourd'hui.

**US backend uniquement (justification)** : les trois fronts désactivent déjà les
actions d'écriture hors ligne (task-304) et savent afficher un `ProblemDetails`
(règle 12). Un front qui appellerait quand même une écriture recevra un refus
explicite au lieu d'un `202` trompeur ; aucun écran nouveau, aucun contrat DTO
modifié.

## Constat établi par lecture du code (2026-09-16)

- `Api/Mail/src/Api/Controllers/V1/MailController.cs` — sur `IsOnlineMode == false`,
  `SendMail` et `SendCancelAndReplace` sérialisent le message et l'empilent
  (`PendingActionTypes.SendMail`) avec `202 Accepted { queued = true }` ; `UpdateReadStatus`,
  déplacement, suppression, favori font de même avec leurs types respectifs et
  rendent `200 { queued = true }`.
- `Api/Mail/src/Application/Services/Implementation/PendingActionService.cs` —
  `ProcessPendingActionsAsync` rejoue la file **dès que** `IsOnlineMode` est vrai
  (jeton PSC présent), déclenché par `POST /api/v1/connection/sync/pending-actions`
  et en fin de cycle de synchronisation.
- `Api/Mail/src/Domain/Entities/MailDb/UserContextInfo.cs` — `IsOnlineMode` vaut
  « un jeton PSC est présent », sans autre condition.
- Origine de la file : l'EPIC E009 (« mode hors-ligne fonctionnel ») visait une
  **coupure réseau** côté poste. Or, sans réseau, le poste n'atteint pas l'API :
  la file **serveur** ne sert en pratique que le cas « réseau présent, jeton PSC
  absent ou expiré ». C'est précisément le cas qu'il faut fermer.

## Règles métier

**RG-1 — Sans session PSC valide, aucune écriture n'est acceptée par le serveur.**
Envoyer, répondre, transférer, annuler-et-remplacer, marquer lu / non lu, signaler,
déplacer, supprimer, restaurer : chacune de ces routes rend **403** en
`application/problem+json` avec un code dédié (« session Pro Santé Connect
requise ») quand la requête ne porte pas de jeton PSC utilisable. Le message est
formulé pour le praticien : il sait que la fonction existe et pourquoi elle est
indisponible. **Rien n'est mis en file.**

**RG-2 — La lecture reste servie.** Dossiers, en-têtes, contenu, pièces jointes déjà
synchronisées, recherche locale, journal d'audit : inchangés hors ligne.

**RG-3 — La compatibilité de la boîte prime.** Une requête avec jeton PSC mais dont
la boîte n'est pas compatible avec la session (task-303, `CanUseImap = false`)
est traitée comme sans PSC pour les écritures : refus, pas de file.

**RG-4 — La file existante est vidée, pas rejouée aveuglément.** Les actions déjà
en attente au moment du déploiement sont rejouées **une dernière fois** au
prochain passage en ligne, **sauf les envois** (`SendMail`), qui sont marqués
« abandonnés » et signalés au praticien dans l'indicateur d'actions en attente,
pour qu'il les renvoie lui-même en connaissance de cause. Aucun message rédigé
sans carte ne part de lui-même.

**RG-5 — L'état de connexion dit la vérité.** `GET /api/v1/connection/status` rend
déjà `canSendEmail = false` hors ligne ; l'US ajoute la même information pour les
autres écritures (`canWrite`), pour que les fronts n'aient pas à deviner.

**RG-6 — Trace d'audit.** Un envoi refusé pour absence de session PSC est tracé
sous le type existant `MailSend` (ou équivalent déjà présent) avec `Success = false` et
le code de refus en `ErrorMessage`. Les autres écritures refusées ne sont pas
tracées une à une (bruit), mais **comptées** dans une métrique. **Aucun nouveau
membre `AuditActionType`** (miroir manuel côté Angular et Blazor).

> ⚠️ **Arbitrage humain requis — non bloquant pour démarrer.**
>
> **Que devient la file hors ligne d'E009 pour les gestes de classement ?** Deux
> lectures du produit coexistent : E009 promet la mise en file des bascules lu /
> non lu, favori, déplacement et suppression ; E016 dit que « classer » est
> désactivé hors ligne. L'US part sur **E016, la plus récente et la plus sûre**
> (RG-1 : tout refusé). Si vous souhaitez conserver la file pour les seuls gestes
> de classement (jamais pour l'envoi), dites-le avant `/start` : la DOD sera
> réduite à l'envoi et à l'annuler-et-remplacer, et l'AIPD devra noter qu'un
> geste de classement peut être posé sans carte.
>
> **Ce qui n'est pas négociable**, quelle que soit la réponse : aucun envoi MSSanté
> ne peut être préparé sans session Pro Santé Connect (garde-fou PO).

## Definition of Done

- [ ] Build passes (0 errors) — `dotnet build HealthPlatform.Api.Mail.sln`
- [ ] Tests pass (0 failures) — `dotnet test HealthPlatform.Api.Mail.sln`
- [ ] Sans jeton PSC : `SendMail`, `SendCancelAndReplace`, réponse/transfert, marquer lu / non lu, signaler, déplacer, supprimer, restaurer rendent **403** `application/problem+json` avec un code dédié ; **aucune ligne** n'est ajoutée à la table des actions en attente
- [ ] Avec jeton PSC mais boîte non compatible (`CanUseImap = false`) : même refus, même absence de file
- [ ] Les routes de lecture (dossiers, en-têtes, contenu, pièces jointes, recherche, audit) sont **inchangées** hors ligne — test d'intégration qui le prouve
- [ ] Les actions en attente préexistantes sont rejouées une dernière fois au retour en ligne, **sauf `SendMail`**, marquées abandonnées et comptées dans `pendingActionsCount` avec un libellé distinct
- [ ] `GET /api/v1/connection/status` expose `canWrite` (faux hors ligne) en plus de `canSendEmail`
- [ ] Trace d'audit en échec sur envoi refusé, sous un type existant ; aucun nouveau membre `AuditActionType`
- [ ] Métrique de comptage des écritures refusées hors ligne (par type d'action)
- [ ] Aucune donnée de santé (sujet, corps, destinataires) dans les logs du chemin de refus
- [ ] Tests unitaires : décision « écriture autorisée » (PSC valide + boîte compatible → oui ; sinon → non) ; traitement de la file préexistante (classements rejoués, envois abandonnés)
- [ ] Tests d'intégration : `POST /api/v1/mail/{folder}/send` sans `X-PSC-Token` → 403 et table des actions en attente vide ; `PUT .../read-status` sans PSC → 403 ; `GET /api/v1/mail/folders` sans PSC → 200
- [ ] Vérification manuelle sur les trois fronts (Blazor, Angular, mobile) : aucune action d'écriture accessible hors ligne ne produit d'erreur technique ; si une route est appelée malgré tout, le message du `ProblemDetails` s'affiche
- [ ] Le document d'EPIC E016 (`/tech-writer`) et la fiche E009 (« mode hors-ligne ») sont mis en cohérence par `/tech-writer` (E009 : file d'attente limitée selon l'arbitrage)

## Manual Test Plan

- **Lancer** : `cd Api/Mail && aspire run --project src/AppHost`, puis un front
  (mobile : `cd Client/Mobile && npm start`).
- **Se placer hors ligne** : se connecter via Keycloak + PSC, ouvrir la boîte, puis laisser le
  jeton PSC expirer sans le rafraîchir (ou retirer l'en-tête `X-PSC-Token` dans une rejouée
  en ligne de commande). Le bandeau « lecture seule » doit s'afficher.
- **Lecture** : ouvrir des dossiers, un message, une pièce jointe déjà synchronisée.
  **Attendu** : tout se lit comme avant.
- **Envoi sans carte** (ligne de commande, bearer Keycloak valide, **sans** `X-PSC-Token`) :
  ```bash
  curl -sk -X POST https://localhost:{port}/api/v1/mail/{dossier}/send \
    -H "Authorization: Bearer {bearer keycloak}" -H "Client-Email: {adresse}" \
    -H "Content-Type: application/json" -d @message.json -i
  ```
  **Attendu** : `403`, corps `application/problem+json`, message « session Pro Santé Connect
  requise » ; **aucune ligne** nouvelle dans la table des actions en attente de la base
  praticien (`docker exec postgres-pgvector psql -U postgres -d {u_…} -c "select \"ActionType\", \"CreatedAt\" from \"PendingActions\" order by \"CreatedAt\" desc limit 5;"`).
- **Classement sans carte** : même rejouée sur marquer lu, déplacer, supprimer.
  **Attendu** : `403`, rien en file (ou, selon l'arbitrage, `200 { queued = true }` pour ces
  seuls gestes — mais **jamais** pour l'envoi).
- **Retour en ligne** : rafraîchir la session PSC. **Attendu** : aucun message rédigé sans carte
  ne part ; l'indicateur d'actions en attente ne montre plus d'envoi en file.
- **Non-régression en ligne** : avec jeton PSC valide, envoyer un message de test vers une
  adresse de test MSSanté. **Attendu** : envoi immédiat comme avant.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — mise en conformité d'une promesse produit existante
- **Exigences DSR honorées** : MSSanté — exigence d'authentification forte du professionnel émetteur (référence DSR à confirmer par le PO humain sur le couloir médecine de ville)
- **INS** : non applicable — aucune manipulation d'identité patient ; l'US porte sur le niveau d'authentification exigé pour écrire
- **Authentification PS** : **c'est l'objet de l'US.** Toute écriture, et en premier lieu tout envoi MSSanté, exige une session Pro Santé Connect (CPS / e-CPS), niveau eIDAS substantiel. Le bearer Keycloak seul suffit à **lire** ce qui est déjà synchronisé, jamais à agir (garde-fou PO « authentification PS sensible »)
- **Habilitations** : inchangées ; l'US resserre le niveau d'authentification requis par action, pas le périmètre des boîtes
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : envoi refusé pour absence de session PSC (trace en échec sous type existant) ; métrique des écritures refusées. Conservation alignée sur le journal existant
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement inchangé
- **AIPD / impact RGPD** : à mettre à jour — préciser que la lecture hors ligne des DSCP synchronisées reste possible avec le seul bearer Keycloak (point d'attention à formaliser), et que toute écriture exige désormais l'identité forte
