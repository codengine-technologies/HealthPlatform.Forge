# todo-task-417 — Changement de boîte : rien de la boîte précédente ne reste

**Repos**: api-mail, client-mobile, client-angular
**Dependencies**: task-412 (mêmes porteurs d'état et même purge)
**Epic**: E020

> **Origine** : audit du périmètre « boîte déléguée » du 2026-10-30
> (`Docs/audits/2026-10-30-audit-boite-deleguee.md`), constats m5, m7 et mineurs clients. Ils ont été
> détachés de task-412 le 2026-10-30, sur décision humaine, après vérification sur le code (mobile
> `cf3505f`, weda2 sur `feature/nova-mss-weda-integration`). `api-mail` porte le catalogue des scénarios
> e2e seulement.

## Objectif

En changeant de boîte, le médecin ne voit plus rien de la précédente : ni conversation IA, ni liste de
patients, ni accueil, ni réglages, ni identité d'expéditeur. Une action faite sur une autre boîte
(rattachement, suppression en attente) ne suspend jamais la boîte qu'il a ouverte.

## Constats vérifiés (2026-10-30)

À la bascule, seuls quatre porteurs d'état sont purgés (`mailbox-scoped-states.ts`) : messages,
patient sélectionné, documents et suppressions en attente. Le reste survit :

| Ce qui survit (mobile) | Cause |
|---|---|
| Conversation IA | `AiChatComponent` vit à la racine. `openFor` réutilise la conversation quand le dossier et les UID sont identiques, sans comparer la boîte : INBOX/27 dans B rouvre la conversation de INBOX/27 dans A |
| Liste de l'onglet Patients | `PatientSearchComponent` charge « patients du jour » une seule fois, dans son constructeur. Les pages d'onglet Ionic ne sont pas recréées |
| Réglages | `UserSettingsService.ensureLoaded()` garde sa promesse pour toujours. Les réglages de A sont relus dans B, et l'enregistrement automatique peut les écrire dans la base de B |
| Identité d'expéditeur | Rechargée au changement, mais une réponse tardive de A peut écraser celle de B : aucune garde de génération |
| Widgets de l'accueil | Rechargés à l'entrée de l'onglet, sans garde contre une réponse tardive |

Autres constats :
- **m7 (mobile, à vérifier sur weda2)** : l'intercepteur suspend la boîte ouverte sur **tout** refus
  d'accès, même pour une requête épinglée à une autre boîte (`MSS_MAILBOX_PIN`). C'est le cas de la
  confirmation de rattachement et des suppressions en attente.
- **Dossier « envoyés »** reconnu par la sous-chaîne `sent` : 1 endroit sur mobile
  (`mail-detail.component.ts`), 3 sur weda2 (`read-receipt.util.ts`, `mail-detail.component.ts`,
  `mail-header.component.ts`). Un dossier « Absent » ou « Consent » serait pris pour les envoyés.
- **weda2** : le flux de notifications ne se rouvre pas après un « Réessayer » réussi. Rapporté par
  l'audit, à confirmer en premier.

## Règles

1. **Tout ce qui appartient à la boîte est purgé à la bascule**, par le mécanisme existant
   (`MAILBOX_SCOPED_STATES` sur mobile, `MSS_RESETTABLE_STORES` sur weda2), et non par un nettoyage écran
   par écran :
   - la conversation IA : fermée et oubliée ;
   - la liste des patients : rechargée pour la nouvelle boîte ;
   - les réglages : promesse oubliée, relus pour la nouvelle boîte, **jamais réécrits** d'une boîte dans
     l'autre ;
   - l'identité d'expéditeur et les widgets : toute réponse arrivée après la bascule est ignorée, par une
     garde de génération.
2. L'état de connexion (« N messages prêts à partir ») est vérifié contre la génération de la boîte.
3. **Requête épinglée** (deux clients) : un refus d'accès sur une requête épinglée à une autre boîte ne
   suspend pas la boîte ouverte. Il est rendu à l'écran qui l'a demandée.
4. **Dossier « envoyés »** reconnu par `FolderType.Sent` sur les deux clients (accusé de lecture,
   annule-et-remplace), jamais par une sous-chaîne du chemin.
5. **weda2** : le flux de notifications se rouvre après un « Réessayer » réussi, si le constat est
   confirmé. Sinon, le `## Develop log` dit pourquoi il ne l'est pas.

## Definition of Done

- [ ] Build passes (0 errors) sur `client-mobile` et `client-angular` (code-only)
- [ ] Tests pass (0 failures) sur chaque client
- [ ] Tests unitaires, chacun vu rouge sur le code d'avant :
  - conversation IA réinitialisée au changement de boîte, même dossier et même UID ;
  - onglet Patients rechargé au changement ;
  - réglages relus au changement, et aucun enregistrement d'une boîte dans l'autre ;
  - réponse tardive ignorée (identité d'expéditeur, widgets) ;
  - requête épinglée refusée sans suspension de la boîte ouverte (deux clients) ;
  - `FolderType.Sent` (deux clients), avec un dossier « Consent » non pris pour les envoyés ;
  - flux de notifications rouvert (weda2), si le constat est confirmé.
- [ ] Scénario **E2E-MAILBOX-007** v1 ajouté dans `Api/Mail/e2e/scenarios.yml` (mobile requis,
      angular requis) : après un changement de boîte, l'assistant, l'onglet Patients et l'accueil ne
      montrent plus rien de la précédente. Implémenté dans chaque client, et prouvé rouge sur le code
      non corrigé.
- [ ] `data-testid` sur tout élément interactif ajouté
- [ ] Aucune donnée de santé en clair dans les logs ni dans le stockage de l'appareil

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil e2e). Mobile :
  `cd Client/Mobile && npm start`. weda2 : via le faux hôte.
- **Changement de boîte** :
  1. Dans la boîte A, ouvrir l'onglet Patients, puis l'assistant sur INBOX/1.
  2. Passer à la boîte B, puis rouvrir l'assistant sur INBOX/1.
  3. Attendu : une nouvelle conversation, l'onglet Patients et l'accueil de B.
- **Réglages** : changer un réglage dans A, passer à B. Attendu : les réglages de B. En revenant à A,
  le réglage de A n'a pas été écrit dans B.
- **Requête épinglée** : depuis la boîte A, rattacher une boîte dont l'opérateur simulé refuse l'accès.
  Attendu : l'erreur s'affiche dans l'écran de rattachement, et A reste ouverte, sans « accès suspendu ».
- **Dossier envoyés** : créer un dossier « Consent », y déplacer un message reçu qui demande un accusé
  de lecture. Attendu : la proposition d'accusé de lecture reste offerte.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — cloisonnement des données entre boîtes côté client
- **Exigences DSR honorées** : référentiel socle MSSanté #2 (clients), ECO.1.2.8 (le client agit sur la
  BAL ouverte)
- **INS** : non applicable — affichage de fiches existantes seulement
- **Authentification PS** : inchangée (PSC)
- **Habilitations** : seules les données de la boîte ouverte s'affichent (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé (changement de boîte déjà tracé côté serveur)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — logique cliente. Aucune donnée persistée sur l'appareil.
- **AIPD / impact RGPD** : inchangé — corrige un affichage croisé entre boîtes
