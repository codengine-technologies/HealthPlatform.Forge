# todo-task-499.md — Tableau de bord : boucles en retard et non affectées

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: task-498
**Epic**: E027

> **Origine.** Demande humaine du 2026-11-27 (« un widget au dashboard offrant une vision globale de l'état de la
> messagerie […] l'urgence des éléments très en retard doit ressortir »), phase de conception validée le même jour :
> `Docs/specs/anneau-de-traitement/` (spécification § 10 et § 11, maquettes section 4, revue de design § 3).
>
> **Lecture de la forge, à confirmer avant `/start`** : la décision 7 offrait deux formes, une tuile « Boucles
> ouvertes » ou l'enrichissement des tuiles existantes. La revue de design préfère la seconde, parce que la tuile
> unique doublerait « À traiter », « Pour moi » et « Bio à acquitter ». « D'accord pour le reste » est lu comme
> l'accord sur cette préférence. Si l'humain veut la tuile unique, cette task se réécrit avant d'être lancée.

## Objectif

Le tableau de bord dit ce qui **traîne** et ce que **personne n'a pris**. Les tuiles existantes gagnent « dont N en
retard », une tuile « Non affectées » s'ajoute, et un clic ouvre la liste correspondante. La légende des anneaux est
à portée depuis le tableau de bord.

### Ce qui est établi

Lecture du code au 2026-11-27 :

- **Tuiles existantes.**
  - weda2 (`libs/mss/src/features/dashboard/`) : « À traiter » (`mss-to-handle-kpi-tile`, lit `toHandleCount` de la
    Boîte de réception) et « Bio à acquitter » (`mss-biology-ack-pending-kpi-tile`,
    `GET api/v1/biology-acks/pending-summary`). Pas de tuile « Pour moi » : la puce de la liste en tient lieu.
  - Mobile (`src/app/features/dashboard/components/`) : « À traiter », « Pour moi », « Bio à acquitter ».
  - Chaque tuile est sous drapeau `dashboard_widget_*` (`Application/Constants/FeatureFlags.cs`).
- **Compteurs.** `ToHandleCount` et `ForMeCount` sont calculés **par requête à chaque appel** de la liste des
  dossiers (`MailController.ApplyWorkCountsAsync`, `MailHandlingRepository.CountToHandleByFolderAsync`,
  `MailAssignmentRepository.CountForMeAsync`). Aucun agrégat n'est tenu à jour.
- **Ouvrir une liste filtrée.** weda2 : paramètres d'adresse lus par `MssMailComponent.listenToQueryParams`
  (`toHandle`, `onlyPendingBiologyAck`, `ackAction`). Mobile : intention d'entrée
  (`MailStateService.requestInboxIntent`). Les vues « À traiter », « Pour moi » et « Bio à acquitter » sont servies
  par pages par le serveur.
- **L'ancienneté** est calculée sur le poste (task-498) : le serveur ne sait pas encore dire « en retard ».
- **Coût déjà connu** : la recherche est linéaire en taille de boîte sur une boîte de 11 000 messages (mesure du
  2026-11-09). Le coût des compteurs de travail n'a pas été mesuré à cette taille.

### Règles

1. **« En retard »** : une boucle ouverte qui a atteint le dernier seuil de sa catégorie (task-498, règles 1 à 3).
   Le serveur applique **la même règle** que les postes, avec les seuils de la boîte.
2. **Tuiles existantes** : chacune ajoute « dont N en retard » sous son nombre, sur son périmètre d'aujourd'hui.
   Rien ne s'affiche à zéro. La tuile « Bio à acquitter » met en avant le nombre de critiques.
   - weda2 : « À traiter », « Bio à acquitter ».
   - Mobile : « À traiter », « Pour moi », « Bio à acquitter ».
3. **Tuile « Non affectées »**, nouvelle, sous le drapeau `dashboard_widget_unassigned` : le nombre de boucles
   ouvertes sans attribution, sur le périmètre de la tuile « À traiter », et « dont N en retard ». Elle n'existe que
   dans une boîte d'au moins **deux personnes actives**.
4. **Un clic ouvre la liste.**
   - Sur le nombre : la vue d'aujourd'hui (« À traiter », « Pour moi », « Bio à acquitter ») ; pour « Non
     affectées », la vue « À traiter » réduite aux messages sans attribution.
   - Sur « dont N en retard » : la même vue, réduite aux boucles en retard. Un filtre actif « En retard » ou « Non
     affecté » est visible en tête de liste et se retire d'un geste.
   - Les listes filtrées sont servies par pages par le serveur : le nombre de lignes est celui de la tuile.
5. **Légende** : une icône d'aide sur la tuile « À traiter » ouvre la légende des anneaux (task-498).
6. **Performance — mesurer avant de choisir** (règle d'or 5).
   - Les compteurs du tableau de bord ont **leur propre appel**. Le chemin de la liste des messages et celui de la
     liste des dossiers ne s'alourdissent pas.
   - Le coût est mesuré **avant et après** sur une boîte d'au moins 10 000 messages, et consigné.
   - Si l'appel coûte plus que le calcul actuel de « À traiter » et « Pour moi » réunis, on ajoute un index sur les
     boucles ouvertes et on re-mesure. Un agrégat tenu à jour ne vient qu'ensuite, si l'index ne suffit pas.
   - Aucun compteur ne parcourt les messages sur le poste.
7. **En direct** : les nombres se mettent à jour quand une boucle est traitée, attribuée ou acquittée, par les
   évènements existants.

### Hors périmètre

- Une tuile unique « Boucles ouvertes » (non retenue, voir l'encadré).
- Les envois sans réponse (décision 9).
- Les deux définitions de « biologie à acquitter » (Boîte de réception pour le résumé, tout dossier pour « à
  traiter ») : relevées au § 12 de la spécification, à traiter dans une task dédiée. Ici, chaque tuile garde son
  périmètre.
- Une tuile « Pour moi » sur weda2.

## Definition of Done

- [ ] Build passes : api-mail, dtos-mss, `nx build weda2`, client-mobile (0 erreur).
- [ ] Tests pass : api-mail, `nx test mss-lib`, `nx test weda2`, client-mobile (0 échec).
- [ ] Tests unitaires (api-mail) de la règle « en retard » côté serveur : chaque catégorie avant et au dernier seuil ;
      biologie critique en heures ; message remis à traiter (la date du geste commande) ; message traité ou hors suivi
      (jamais en retard) ; seuils de la boîte modifiés. Chacun vu rouge.
- [ ] Test qui prouve que la règle du serveur et celle des postes **s'accordent** : mêmes cas, même verdict (jeu de
      cas partagé ou test d'intégration qui compare). Vu rouge.
- [ ] Test d'intégration de bout en bout pour l'appel des compteurs du tableau de bord : sur une boîte portant 3
      courriers à traiter dont 1 au-delà du dernier seuil, 1 biologie critique à acquitter depuis plus de 72 heures et
      1 message attribué à la personne, la réponse réelle rend les nombres et les « en retard » attendus pour « À
      traiter », « Pour moi », « Bio à acquitter » et « Non affectées ». Cas d'échec : un message traité, un « Pour
      info » et un message antérieur au suivi ne comptent nulle part. Vu rouge (règle 1b).
- [ ] Test d'intégration des listes filtrées « en retard » et « non affecté » : les messages rendus sont exactement
      ceux que les compteurs comptent, page par page, relus dans la réponse réelle. Vu rouge.
- [ ] Test d'intégration en boîte partagée (règle 14) : le délégataire traite un message en retard ; le titulaire
      relit les compteurs, qui ont baissé ; la trace du geste porte le délégataire. « Non affectées » est absent de la
      réponse pour une boîte à une seule personne active. Vu rouge.
- [ ] **Mesure** consignée dans le `## Develop log` : coût de l'appel des compteurs et de la liste des dossiers, avant
      et après, sur une boîte d'au moins 10 000 messages (`Tools/timing/measure.sh` ou `DbOperationScope`) ; plan
      d'exécution relu ; décision « index ou non » justifiée par les chiffres.
- [ ] Toute migration (index) relue : aucune donnée modifiée ni supprimée, descente propre (règle 7c).
- [ ] Drapeau `dashboard_widget_unassigned` déclaré et semé comme les autres ; tuile absente quand il est éteint.
- [ ] dtos-mss : contrats ajoutés publiés, api-mail bumpé ; `python Tools/contracts/contract_impact.py check` sans
      impact non adapté.
- [ ] Tests de composant, weda2 et mobile, vus rouges : « dont N en retard » affiché, absent à zéro ; tuile « Non
      affectées » absente en boîte à une personne ; chaque clic ouvre la bonne vue avec le bon filtre ; le filtre
      actif est visible et se retire ; l'icône d'aide ouvre la légende ; état « indisponible » si l'appel échoue.
- [ ] `data-testid` sur chaque nombre, chaque « en retard », la tuile et les filtres ; aucun texte en dur hors de la
      convention de chaque client.
- [ ] Mobile : référence Stitch de l'écran `home` mise à jour (`/stitch-design`, best-effort).
- [ ] Scénario **E2E-DASH-002** (version 1, `mobile: requis`, `angular: requis`) ajouté à
      `Api/Mail/e2e/scenarios.yml` et implémenté dans les deux clients : en boîte partagée, le test dépose un
      courrier à traiter arrivé au-delà du dernier seuil et un autre arrivé aujourd'hui, tous deux sans attribution.
      La tuile « À traiter » annonce « dont 1 en retard » et la tuile « Non affectées » compte les deux, comme le
      serveur les compte. Le praticien touche « dont 1 en retard » : la liste ne montre que le courrier ancien, filtre
      « En retard » visible. Il le marque « Traité » ; de retour au tableau de bord, « en retard » a disparu et « Non
      affectées » a baissé de un.
- [ ] E2E-DASH-001 rejoué vert, attendu inchangé.
- [ ] Aucune donnée de santé dans les journaux ni dans la réponse des compteurs (des nombres seulement).

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil de développement habituel).
- weda2 : `cd Client/Angular/front && npm run start:weda2`, ouvrir « Tableau de bord ».
- Mobile : `cd Client/Mobile && npm start`, onglet « Accueil ».
- Données : une boîte partagée avec un délégataire ; plusieurs courriers à traiter dont un arrivé il y a plus de 14
  jours ; un compte rendu de biologie critique à acquitter depuis plus de 72 heures ; un message attribué à soi.
- Référence visuelle : `Docs/specs/anneau-de-traitement/maquettes.html`, section 4, « Alternative : enrichir les
  tuiles existantes ».

1. Tableau de bord : « À traiter » affiche son nombre et « dont N en retard » ; « Bio à acquitter » met en avant le
   critique et son retard ; « Non affectées » affiche les messages que personne n'a pris.
2. Cliquer « dont N en retard » sous « À traiter » : la liste ne montre que les boucles en retard, le filtre « En
   retard » est visible. Le retirer : la vue « À traiter » complète revient.
3. Cliquer « Non affectées » : la liste ne montre que les messages sans attribution. En attribuer un : de retour au
   tableau de bord, le nombre a baissé.
4. Traiter le courrier en retard depuis un second poste (délégataire) : le tableau de bord du titulaire se met à
   jour sans rechargement.
5. Icône d'aide : la légende des anneaux s'ouvre.
6. Ouvrir une boîte à une seule personne : pas de tuile « Non affectées ».
7. Refaire 1 à 6 sur le mobile, avec la tuile « Pour moi ».

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du cabinet).
- **Vague Ségur** : hors Ségur — aide à l'organisation du cabinet, aucune exigence DSR nouvelle.
- **Exigences DSR honorées** : non applicable.
- **INS** : non applicable — les compteurs ne portent aucun patient.
- **Authentification PS** : inchangée — session PSC (e-CPS) de la messagerie.
- **Habilitations** : inchangées. Les compteurs sont ceux de la boîte, vus de toute personne rattachée et active ;
  « Pour moi » est celui de la personne connectée. Sans verdict récent de l'opérateur, aucun compteur n'est rendu
  (règle 14).
- **Interop CI-SIS** : non applicable.
- **Tracé PGSSI-S** : aucun acte nouveau. Lire des compteurs n'ouvre aucune donnée de santé ; ouvrir un message
  depuis une liste filtrée est tracé comme aujourd'hui, au nom de la personne réelle.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui — compteurs calculés dans la base de la boîte, environnement HDS existant ; aucune donnée
  de santé nouvelle.
- **AIPD / impact RGPD** : inchangée — des nombres, aucune donnée de santé ni décision automatisée.
