# todo-task-359.md — Intégration Weda : les comptes rendus de biologie reçus arrivent dans la bannette HPRIM, sans WMickey

> ⏸️ **ON HOLD (décision humaine 2026-10-10)** — retirée du backlog actif, conservée pour la trace.
> L'EPIC E019 change de stratégie : la nouvelle expérience se limite à l'**import des documents à
> la demande du médecin**. La réception, la biologie et l'injection HPRIM restent à WMickey. Le
> mode exclusif et le canal serveur Weda → api-mail de l'amendement 2 de l'ADR-007 sont abandonnés
> (amendement 3 de l'ADR-007, dépôt Weda).
>
> **Ce qui reste** : les comptes rendus de biologie continuent d'arriver en bannette par WMickey.
>
> **Pour réactiver** : une décision humaine qui rouvre le mode exclusif (nouvel amendement de
> l'ADR-007), puis redéplacer ce fichier dans `tasks/` et `/start 359`.

**Repos**: api-mail
**Dependencies**: done-task-358 (API d'intégration et canal serveur Weda → api-mail)
**Epic**: E019
**Single frontend**: true — aucun client de la forge n'est touché. L'injection en bannette est
faite par Weda, hors forge (voir « Partie Weda »).
**Priorité**: **1** — c'est le circuit des résultats de biologie. Pour un cabinet en nouvelle
expérience, WMickey est coupé : sans cette tâche, **aucun CR de biologie n'arriverait dans la
bannette HPRIM** du médecin.

> **Origine.** Amendement 2 de l'ADR-007 du dépôt Weda (2026-10-09), décisions A4 et A5. La
> réception de la biologie quitte la chaîne WMickey, jugée non fiable par l'humain :
> - le jeton PSC est transporté dans la file RabbitMQ, où il peut expirer ;
> - le mot-clé `Weda` est posé **avant** l'import, si bien qu'un import en échec est perdu ;
> - il n'y a pas de nouvelle tentative ;
> - seule l'INBOX est lue.
>
> Le serveur Weda va désormais chercher les CR de biologie dans api-mail et les injecte avec le code
> HPRIM existant. La mémoire « déjà pris en charge » est un **mot-clé IMAP**, ce qui évite tout
> changement de schéma dans la base Weda.

## Ce qui existe (constaté dans le code le 2026-10-09)

- **api-mail** :
  - à la synchronisation, les IHE_XDM sont analysés (`IheXdmProcessingService`,
    `CdaParsingService` › `ParseIheXdmZip`). Les documents médicaux sont créés
    (`MailMedicalDocument` : INS, OID, LOINC, catégorie, résultats de biologie), puis promus dans
    `MailRepository`. Les fichiers d'un document sont rangés en `MailAttachment` (`DocumentId`) ;
  - **le XML brut du CDA n'est pas conservé en tant que tel**. L'archive IHE_XDM d'origine reste
    lisible : cache en base, sinon IMAP ;
  - **aucun mot-clé IMAP n'est lu ni posé** : seuls `\Seen`, `\Flagged` et `\Deleted` sont
    manipulés (`FlagPropagationService`, `ImapMoveHelper`) ;
  - `POST /api/v1/sync/start` déclenche une synchronisation, protégée par un verrou Redis ;
  - l'API d'intégration `api/v1/integration` existe (task-358).
- **WMickey** (référence, sans modification) : il pose le mot-clé IMAP `Weda` sur ce qu'il a pris
  en charge (`MailKitImapClient.MarkAsProcessedAsync`), et ne retraite jamais un message qui le
  porte. Ce sens est **repris tel quel** : en cas de retour arrière vers WMickey, il ne réinjectera
  pas ce que Weda a déjà injecté.
- **Weda** (hors forge) :
  - `HprimService.InjectCdaWithIns(cabId, userId, xmlDuCda, ins)` injecte un CR de biologie à
    partir du XML brut. Il rend `INSERTED`, `DUPLICATED`, `NO_ACTION` (pas un CR-BIO) ou `ERROR` ;
  - en production, l'index unique `Hpm_Hash_Idx (Cab_ID, Hpm_Hash)` refuse un CDA identique en
    double. Le hash porte sur les traits et le XML.

## Objective

1. **Mots-clés IMAP `Weda` et `WedaClasse`** (le second est utilisé par task-360) :
   - lus à la synchronisation **dans tous les dossiers**, et conservés par mail ;
   - exposés sur le mail dans les contrats existants : `isHandledByWeda` (`Weda`) et `isFiledInWeda`
     (`WedaClasse`) ;
   - **`POST api/v1/integration/mails/{mailId}/keywords`** `{ "keyword": "Weda" | "WedaClasse" }`
     pose le mot-clé sur le serveur IMAP et dans api-mail. Il est **idempotent**, et **refuse tout
     autre mot-clé** (`400` `ProblemDetails`).
2. **`GET api/v1/integration/biology/pending`** → la liste des **comptes rendus de biologie** de la
   boîte dont le mail **ne porte pas** `Weda` :
   - tous dossiers confondus, y compris la corbeille ;
   - du plus ancien au plus récent, 50 au plus ;
   - pour chacun : `mailId`, `medicalDocumentId`, `receivedAt`, `ins` et `insOid` (s'ils sont
     présents). **Aucun contenu**.
   - « Compte rendu de biologie » : le critère est aligné sur celui de Weda (`CrBiologie`, volet
     CR-BIO du CI-SIS). Le critère retenu est écrit dans le `## Develop log`.
3. **`GET api/v1/integration/medical-documents/{id}/cda`** → le XML **brut** du CDA, en
   `application/xml` :
   - **relu à la demande dans l'archive IHE_XDM d'origine**, sans stockage supplémentaire. Ce sont
     les mêmes octets que ceux que lisait WMickey, donc le même `Hpm_Hash` ;
   - `404` `ProblemDetails` si l'archive n'est plus lisible ;
   - **la lecture est tracée** dans le journal d'audit (`AuditActionType`), comme un téléchargement
     de pièce jointe (task-186).
4. Toutes ces routes sont fermées si `weda_integration` est inactif (`403`, règle de task-358).

## Partie Weda (hors forge, faite en dehors de `/develop`)

Elle est nécessaire pour que la tâche soit complète (règle 11).

- **Un minuteur global** dans l'application Angular 11 de Weda, sur toutes les pages, comme
  aujourd'hui celui de WMickey. Toutes les 2 minutes, pour un praticien d'un cabinet
  `weda_integration`, il appelle `POST /api/mss/nova/reception`. Le **minuteur WMickey est coupé**
  pour ce cabinet (`mickey.module.ts` › `canInitializeWeda`).
- **`POST /api/mss/nova/reception`**, côté serveur Weda, avec le canal de task-358 :
  1. `POST /api/v1/sync/start` ;
  2. `GET …/biology/pending` ;
  3. pour chaque document, `GET …/cda`, puis `HprimService.InjectCdaWithIns(cabinet, praticien,
     xml, ins)` ;
  4. si le résultat est `INSERTED`, `DUPLICATED` ou `NO_ACTION`, `POST …/keywords {Weda}`. Si
     c'est `ERROR` ou un échec réseau, rien n'est posé, et le document est retraité au passage
     suivant.
- **Journaux** : nombre de documents traités et résultat par `medicalDocumentId`. Jamais d'INS ni
  de contenu.

## Definition of Done

- [ ] Build passes (0 errors) ; Tests pass (0 failures, hors flaky préexistants documentés)
- [ ] Tests unitaires :
  - [ ] la liste blanche des mots-clés
  - [ ] l'idempotence de la pose
  - [ ] le filtre « CR de biologie sans `Weda` »
  - [ ] la relecture du CDA dans l'IHE_XDM, avec une archive absente et un document absent
- [ ] Test d'intégration de bout en bout pour `POST /api/v1/integration/mails/{id}/keywords` :
  - [ ] après la pose de `Weda`, le mail porte `isHandledByWeda = true` dans `GET` du mail ;
  - [ ] **le mot-clé est présent sur le serveur IMAP de test**, et il est toujours lu après une
    nouvelle synchronisation ;
  - [ ] cas d'échec : `400` `ProblemDetails` pour un mot-clé hors liste ;
  - [ ] vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout pour `GET /api/v1/integration/biology/pending` :
  - [ ] le CR de biologie du seed (`cr-bio-a-acquitter`) est listé, avec son `medicalDocumentId` ;
  - [ ] un message sans CR de biologie n'est pas listé ;
  - [ ] après la pose de `Weda`, il **disparaît** de la liste ;
  - [ ] un CR déplacé dans un autre dossier **reste** listé ;
  - [ ] cas d'échec : `403` quand `weda_integration` est inactif ;
  - [ ] vu rouge (règle 1b)
- [ ] Test d'intégration de bout en bout pour `GET /api/v1/integration/medical-documents/{id}/cda` :
  - [ ] le corps est le XML du CDA du seed, octet pour octet identique au fichier de l'IHE_XDM ;
  - [ ] la lecture apparaît dans le journal d'audit ;
  - [ ] cas d'échec : `404` `ProblemDetails` pour un document inconnu ;
  - [ ] vu rouge (règle 1b)
- [ ] Aucune donnée de santé dans les logs : ni INS, ni contenu CDA, ni nom de patient
- [ ] Swagger : routes, schémas et codes d'erreur documentés
- [ ] Partie Weda faite et validée (règle 11) : voir Manual Test Plan

## Manual Test Plan

1. Backend : `cd Api/Mail && dotnet run --project src/AppHost`. Weda en `https://localhost:44300`,
   avec le cabinet de test en `weda_integration`.
2. Envoyer à la boîte de test un message portant un IHE_XDM de compte rendu de biologie : le CDA
   du corpus de test ANS, déjà utilisé par le seed e2e.
3. Rester sur **une page Weda quelconque**, l'agenda par exemple, sans ouvrir Échanges. En moins de
   2 minutes, le résultat apparaît dans la bannette HPRIM (`FolderMedical/HprimForm.aspx`), **une
   seule fois**.
4. Dans un client IMAP de test, le message porte le mot-clé `Weda`.
5. **Pas de doublon** : recharger la page plusieurs fois et attendre deux passages. La bannette ne
   contient toujours qu'un seul résultat.
6. **Reprise sur échec** : couper api-mail le temps d'un passage, puis le relancer. Le résultat
   arrive au passage suivant.
7. **Message rangé avant traitement** : arrêter Weda, recevoir un nouveau CR de biologie, le ranger
   dans un dossier depuis weda2 ouvert seul, puis rouvrir Weda. Le résultat arrive quand même en
   bannette.
8. **WMickey coupé** : dans les outils de développement, aucune requête vers
   `…/api/mickey/syncMail/sync` pour ce cabinet.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — messagerie MSSanté intégrée au logiciel ; intégration des CR de biologie
  structurés
- **Exigences DSR honorées** : continuité de l'intégration des CR de biologie reçus par MSSanté
  dans le logiciel. Le comportement est le même qu'avec WMickey, avec un rattrapage fiabilisé.
  Aucune exigence DSR nouvelle.
- **INS** : l'INS portée par le CDA est transmise à Weda **telle quelle**, pour le rapprochement de
  la bannette (`InjectCdaWithIns`, logique existante). Aucune identité n'est créée ni qualifiée par
  cette tâche. L'INS transite dans le corps JSON (jamais dans une URL), et n'apparaît jamais dans
  un log.
- **Authentification PS** : PSC / e-CPS, niveau eIDAS substantiel. Accès IMAP en XOAUTH2 avec le
  jeton PSC du praticien, obtenu par api-mail auprès du proxy à chaque appel : **aucun jeton
  transporté dans une file**.
- **Habilitations** : boîte du praticien connecté (`Client-Email`). Injection dans la bannette du
  cabinet et du praticien de la session Weda.
- **Interop CI-SIS** : CDA R2, volet CR-BIO, dans une enveloppe IHE_XDM. Le XML est transmis
  **sans transformation**. Le parsing reste celui de Weda (`CrBiologie`) pour la bannette, et
  celui d'`interop-cda` dans api-mail.
- **Tracé PGSSI-S** : la lecture du CDA par le logiciel hôte est journalisée dans le journal
  d'audit, avec la même durée de conservation que les téléchargements de pièce jointe. La pose du
  mot-clé est journalisée techniquement.
- **Consentement patient** : non applicable — intégration d'un document reçu dans le dossier du
  professionnel destinataire
- **Référentiels métier** : LOINC (types de documents et analyses du CR-BIO)
- **Hébergement HDS** : oui — le CDA transite entre deux services hébergés (api-mail et Weda), en
  HTTPS. Rien n'est stocké en plus dans api-mail.
- **AIPD / impact RGPD** : inchangé — même finalité que la chaîne WMickey remplacée

## Jalon de bascule (hors tâche)

Un cabinet ne passe réellement en mode exclusif qu'après task-360 (classement) et task-361 (envoi
depuis Weda). Il faut aussi que sa boîte d'envoi WMickey soit vide. D'ici là,
`weda_integration` n'est activée que sur un cabinet de test.
