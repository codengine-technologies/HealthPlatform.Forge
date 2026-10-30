# todo-task-412 — Clients : déconnexion et changement de boîte sans rien de la précédente

**Repos**: api-mail, client-mobile, client-angular
**Dependencies**: task-407 (mêmes écrans de lecture et de rédaction, et le From = boîte ouverte côté mobile)
**Epic**: E020

> **Origine** : audit du périmètre « boîte déléguée » du 2026-10-30
> (`Docs/audits/2026-10-30-audit-boite-deleguee.md`). Constats M1, M8, m5, m6, m7, et les mineurs
> clients (identité d'expéditeur, dossier « envoyés », `{{SenderRPPS}}`, flux de notifications).
> `api-mail` porte le catalogue des scénarios e2e seulement.

## Objectif

Sur un appareil partagé, un médecin qui se connecte n'arrive jamais dans la boîte du précédent. En
changeant de boîte, il ne voit plus rien de la précédente : assistant, patients, accueil, réglages,
fenêtres ouvertes. Un délégataire utilise l'assistant IA dans la boîte qu'il a ouverte.

## Règles

1. **Déconnexion (mobile, M1)** : elle vide la boîte ouverte, la liste des boîtes et tous les états
   de boîte :
   - messages, patients, conversation IA, réglages, compteurs, identité d'expéditeur ;
   - modales.

   La connexion suivante, y compris par e-CPS sans rechargement de page, repasse par le choix de
   boîte. weda2 : vérifier que sa déconnexion obtient le même résultat, et le garantir sinon.
2. **La boîte ouverte, pas le compte (M8, convention `adresse-de-la-boite-ouverte`)** :
   - le flux de l'assistant IA (`fetch` direct) envoie `Client-Email` = boîte ouverte ;
   - toute adresse qui représente « d'où j'agis » est relue sur les deux clients. Chaque usage restant
     de l'adresse du compte est justifié dans le `## Develop log`.
3. **Changement de boîte (m5)**. Rien de la boîte précédente ne reste affiché ni réutilisable :
   - conversation IA ;
   - liste de l'onglet Patients ;
   - widgets de l'accueil (une réponse tardive de la boîte précédente est ignorée) ;
   - réglages en cache : rechargés, jamais réécrits d'une boîte dans l'autre ;
   - identité d'expéditeur : une réponse tardive est ignorée.

   L'état de connexion (« N messages prêts à partir ») est vérifié contre la génération de la boîte.
4. **Accès suspendu (m6)** : les modales de rédaction et d'assistant sont fermées, et les flux temps
   réel fermés, quand l'écran « accès suspendu » s'affiche.
5. **Requête épinglée (m7, deux clients)** : un refus d'accès sur une requête épinglée à une autre
   boîte (confirmation de rattachement, suppressions en attente) ne suspend pas la boîte ouverte. Il
   est rendu à l'écran qui l'a demandée.
6. **Mineurs clients** :
   - dossier « envoyés » reconnu par `FolderType.Sent`, jamais par la sous-chaîne `sent`, sur les deux
     clients (accusé de lecture, annule-et-remplace) ;
   - weda2 : `{{SenderRPPS}}` vient du RPPS de la personne, jamais de la partie locale de l'adresse ;
   - weda2 : le flux de notifications se rouvre après un « Réessayer » réussi.

## Definition of Done

- [ ] Build passes (0 errors) sur `client-mobile` et `client-angular` (code-only)
- [ ] Tests pass (0 failures) sur chaque client
- [ ] UI component / unit tests, chacun vu rouge sur le code d'avant :
  - déconnexion, avec l'état de boîte vidé et le garde qui repasse par le choix ;
  - en-têtes du flux IA ;
  - conversation IA réinitialisée au changement de boîte ;
  - onglet Patients et widgets rechargés, avec réponse tardive ignorée ;
  - réglages rechargés au changement ;
  - modales fermées à la suspension ;
  - requête épinglée refusée sans suspension de la boîte ouverte ;
  - `FolderType.Sent` ;
  - `{{SenderRPPS}}` ;
  - flux de notifications rouvert.
- [ ] Scénario **E2E-SESSION-004** v1 ajouté dans `Api/Mail/e2e/scenarios.yml` (mobile requis,
      angular requis) : une personne se déconnecte, une autre se connecte sur le même appareil, et
      n'arrive jamais dans la boîte de la première (relecture du `Client-Email` envoyé et de la
      liste affichée). Implémenté dans chaque client.
- [ ] Scénario **E2E-MAILBOX-007** v1 ajouté (mobile requis, angular requis) : après un changement de
      boîte, l'assistant, l'onglet Patients et l'accueil ne montrent plus rien de la précédente.
      Implémenté dans chaque client.
- [ ] Scénario **E2E-AI-002** v1 ajouté (mobile requis, angular requis) : un délégataire interroge
      l'assistant dans la boîte du titulaire, et la réponse porte sur la boîte ouverte. Implémenté
      dans chaque client.
- [ ] Trou du filet : M1 et M8 étaient visibles du médecin sans que `/e2e` les attrape.
      E2E-SESSION-004 et E2E-AI-002 sont prouvés rouges sur le code non corrigé, et une ligne est
      ajoutée dans `conventions/e2e.md`.
- [ ] `data-testid` sur tout élément interactif ajouté
- [ ] Aucune donnée de santé en clair dans les logs ni dans le stockage de l'appareil

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil e2e). Mobile :
  `cd Client/Mobile && npm start`. weda2 : via le faux hôte.
- **Déconnexion** :
  1. Le titulaire e2e ouvre `boite-praticien` puis se déconnecte.
  2. Le délégataire e2e se connecte sur le même onglet, sans recharger.
  3. Attendu : l'écran de choix de boîte, ni les messages ni les dossiers du titulaire.
- **Changement de boîte** :
  1. Dans la boîte A, ouvrir l'onglet Patients et une conversation IA sur un message.
  2. Passer à la boîte B, puis rouvrir l'assistant sur un message de même numéro.
  3. Attendu : une nouvelle conversation, l'onglet Patients et l'accueil de B.
- **Assistant d'un délégataire** : le délégataire ouvre la boîte du titulaire et interroge
  l'assistant. Attendu : une réponse, ni 403 ni 404.
- **Suspension** : un brouillon est ouvert quand l'opérateur simulé refuse le délégataire. Attendu :
  la modale se ferme sur « accès suspendu ».

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — sécurité des postes partagés
- **Exigences DSR honorées** : référentiel socle MSSanté #2 (clients), ECO.1.2.8 et ECO.1.2.11 (le
  client agit sur la BAL ouverte). PGSSI-S : confidentialité sur poste partagé.
- **INS** : non applicable — affichage de fiches existantes seulement
- **Authentification PS** : PSC / e-CPS. La connexion d'une autre personne repart de zéro.
- **Habilitations** : seules les données de la boîte ouverte, et seulement sous accès valide (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé (déconnexion et changement de boîte déjà tracés côté serveur)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — logique cliente. Aucune donnée persistée sur l'appareil.
- **AIPD / impact RGPD** : inchangé — corrige une exposition sur poste partagé
