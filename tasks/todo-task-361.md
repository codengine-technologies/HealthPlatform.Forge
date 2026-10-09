# todo-task-361.md — Intégration Weda : « Envoyer par MSSanté » depuis un document Weda ouvre la rédaction de la nouvelle messagerie

**Repos**: api-mail, client-angular
**Dependencies**: done-task-358 (API d'intégration et canal serveur Weda → api-mail)
**Epic**: E019
**Single frontend**: true — seul weda2 (client-angular) est embarqué dans Weda. Blazor et mobile
n'ont pas d'hôte Weda (raison fonctionnelle).
**Priorité**: **1** — en mode exclusif, WMickey est coupé, et la rédaction de l'ancien écran ne doit
plus servir. Sans cette tâche, **les boutons « Envoyer par MSSanté » du dossier patient ne
fonctionnent plus** pour un cabinet basculé : la page Échanges n'affiche que weda2, et la boîte
d'envoi WMickey n'est plus vidée.

> **Origine.** Amendement 2 de l'ADR-007 du dépôt Weda (2026-10-09), décision A7 :
> - le serveur Weda dépose le document et le destinataire dans un **brouillon api-mail** ;
> - puis la page hôte demande à weda2 `open-draft { draftId }` ;
> - **aucun fichier ne passe par le pont**.
>
> C'est le premier message du pont dans le sens hôte → weda2. C'est aussi la fonctionnalité F6 de
> l'EPIC E009 (« envoyer depuis n'importe quel document »), restée à 🟡 côté LGC.
>
> Constat du POC : avec le switch actif, ces boutons arrivent déjà sur une page où la rédaction de
> l'ancien écran est masquée.

## Ce qui existe (constaté dans le code le 2026-10-09)

- **Weda** (hors forge) :
  - les boutons d'envoi ouvrent `/FolderMedical/WedaEchanges/?Mode=1&Fil={FileStreamId}&Pat={id}&crypt=…`
    (`SendFileEchangesProvider`, `HistoriqueUCForm`, `EtatCivilUCForm` avec `Add=1`, etc.) ;
  - `Default.aspx.cs` valide la signature `crypt`, prépare l'aperçu du document, et expose
    l'adresse MSSanté du patient quand le ciblage est autorisé (`MSSPatientTargeting`) ;
  - un CDA envoyé doit partir dans une enveloppe IHE_XDM (`IheXdmService`, ADR-004).
- **api-mail** : une API de brouillons existe (`POST /mail/drafts`, `MailDraftService`). Ce qu'elle
  accepte en pièces jointes est **à vérifier** : la forge le consigne dans le `## Develop log`.
- **client-angular** :
  - la rédaction ne se pré-remplit que par `MailEventService.openCompose$`, un service **propre au
    composant**, que le shell ne peut pas atteindre ;
  - aucune route ne permet d'ouvrir un brouillon par son identifiant ;
  - le pont n'accepte aujourd'hui que des **réponses** de l'hôte, jamais de **demande**.

## Objective

1. **api-mail** — **`POST api/v1/integration/drafts`**, en multipart :
   - entrée : destinataires (adresses MSSanté), objet facultatif, une ou plusieurs pièces jointes ;
   - le brouillon est créé dans la boîte `Client-Email` ;
   - réponse `{ "draftId": … }` ;
   - les pièces respectent les limites de taille et de type des brouillons existants (`400` /
     `413` en `ProblemDetails`) ;
   - route fermée si `weda_integration` est inactif ;
   - si l'API de brouillons existante couvre déjà ce besoin, la route d'intégration la réutilise
     sans dupliquer la logique.
2. **client-angular** :
   - **le pont accepte des demandes de l'hôte**. Un seul type en v1, **`open-draft { draftId }`**,
     avec les mêmes contrôles d'origine et de fenêtre émettrice. weda2 répond `{ ok: true }` une
     fois la rédaction ouverte, ou une erreur du contrat ;
   - **ouvrir la rédaction sur un brouillon** depuis le shell (route ou service atteignable),
     avec le destinataire et les pièces jointes du brouillon. Le praticien relit, complète et
     envoie, ou abandonne ;
   - le tout est conditionné par `MSS_PATIENT_RECORD_GATEWAY.available()`, ou son équivalent pour le
     sens hôte → weda2 : sans intégration disponible, `open-draft` est refusé avec `unsupported` ;
   - **faux hôte de test** (task-360) étendu à `open-draft`.

## Partie Weda (hors forge, faite en dehors de `/develop`)

Elle est nécessaire pour que la tâche soit complète (règle 11).

- Pour un cabinet `weda_integration`, quand `Default.aspx` est ouverte en mode rédaction
  (`Mode=1`, `Fil`, `Pat`, `crypt` valide), le serveur Weda :
  1. lit le document. **Un CDA est emballé en IHE_XDM** par `IheXdmService`, comme dans l'ancien
     écran ;
  2. détermine le destinataire : l'adresse MSSanté du patient si son ciblage est autorisé, sinon
     aucun ;
  3. crée le brouillon par `POST api/v1/integration/drafts`.

  La page hôte demande ensuite à weda2 `open-draft { draftId }`.
- En cas d'échec à n'importe quelle étape, un message clair s'affiche dans le bandeau. Rien n'est
  envoyé.

## Definition of Done

- [ ] Build passes (0 errors) sur api-mail et client-angular ; Tests pass (0 failures, hors flaky
  préexistants documentés)
- [ ] **api-mail** — test d'intégration de bout en bout pour `POST /api/v1/integration/drafts` :
  - [ ] le brouillon créé est relu par l'API de brouillons existante, avec le bon destinataire et
    la pièce jointe **octet pour octet** ;
  - [ ] cas d'échec : `413` ou `400` `ProblemDetails` pour une pièce trop lourde ou d'un type
    refusé, et `403` si `weda_integration` est inactif ;
  - [ ] vu rouge (règle 1b)
- [ ] **Angular** — tests unitaires du pont, rouges d'abord :
  - [ ] une demande `open-draft` de l'hôte est traitée et reçoit une réponse portant le même
    `requestId` ;
  - [ ] une demande venant d'une autre origine ou d'une autre fenêtre est ignorée ;
  - [ ] sans intégration disponible, la réponse est `unsupported`
- [ ] **Angular** — tests de composant : la rédaction ouverte sur un brouillon montre le
  destinataire et la pièce jointe, et l'abandon ne laisse rien partir
- [ ] Scénario **E2E-WEDA-002**, version 1, ajouté dans `Api/Mail/e2e/scenarios.yml` :
  - titre : « Envoyer un document du dossier patient par la nouvelle messagerie » ;
  - clients : `angular: requis`, `mobile: non-applicable — l'application mobile n'est pas
    embarquée dans Weda` ;
  - implémenté dans client-angular avec le faux hôte de test.
- [ ] `data-testid` inchangés sur la rédaction existante ; libellés FR en dur pour les nouveaux
  messages
- [ ] Aucune donnée de santé dans les logs : ni contenu de pièce, ni adresse patient
- [ ] Partie Weda faite et validée (règle 11) : voir Manual Test Plan

## Manual Test Plan

1. Backend : `cd Api/Mail && dotnet run --project src/AppHost`. weda2 :
   `cd Client/Angular/front && .\serve-weda2.ps1`. Weda en `https://localhost:44300`, cabinet de
   test en `weda_integration`.
2. Dans le dossier d'un patient Weda, sur un document PDF de l'historique, cliquer sur
   « Envoyer par MSSanté ». La page Échanges s'ouvre sur la **rédaction de weda2**, avec le PDF en
   pièce jointe.
3. Même geste depuis l'état civil d'un patient dont le ciblage MSSanté est autorisé (« Mon espace
   santé ») : son adresse est déjà en destinataire.
4. Même geste sur un document **CDA** : la pièce jointe est l'enveloppe **IHE_XDM**. L'envoyer à sa
   propre adresse, puis la rouvrir dans weda2 : elle est reconnue comme document médical.
5. **Abandon** : fermer la rédaction sans envoyer. Rien n'est parti, et le brouillon reste dans les
   brouillons.
6. **Non-régression** : un cabinet sans `weda_integration` garde la rédaction de l'ancien écran.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — messagerie MSSanté intégrée au logiciel
- **Exigences DSR honorées** : F6 de l'EPIC E009 (« envoi depuis n'importe quel document du
  logiciel »). Un document CDA est envoyé dans son enveloppe IHE_XDM, conformément au CI-SIS
  MSSanté.
- **INS** : un CDA envoyé porte l'INS qu'il contient déjà, sans modification. Aucune identité
  n'est créée ni modifiée. L'adresse patient n'est proposée que si le ciblage est autorisé (règle
  existante `MSSPatientTargeting`).
- **Authentification PS** : PSC / e-CPS, niveau eIDAS substantiel. **L'envoi reste un geste du
  praticien dans weda2**, avec sa session PSC ; le brouillon seul ne part jamais.
- **Habilitations** : la signature `crypt` des URL Weda est validée côté serveur. Le document doit
  appartenir au cabinet de la session. La boîte est celle du praticien.
- **Interop CI-SIS** : CDA R2 emballé en IHE_XDM (`IheXdmService` de Weda, ADR-004). Les autres
  documents sont envoyés tels quels.
- **Tracé PGSSI-S** : la création du brouillon par le logiciel hôte est journalisée techniquement.
  L'envoi est tracé par api-mail, comme tout envoi.
- **Consentement patient** : un envoi au patient (Mon espace santé) respecte les règles de ciblage
  et de consentement existantes (`MSSPatientTargeting`, consentement MSSanté du patient). Rien de
  nouveau.
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — le document transite entre Weda et api-mail, deux services hébergés,
  en HTTPS. Le brouillon est stocké dans la boîte MSSanté du praticien.
- **AIPD / impact RGPD** : inchangé — même finalité que l'envoi depuis l'ancien écran
