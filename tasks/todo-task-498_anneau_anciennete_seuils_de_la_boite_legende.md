# todo-task-498.md — Anneau : ancienneté, seuils de la boîte, préférences et légende

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: task-497
**Epic**: E027

> **Origine.** Demande humaine du 2026-11-27 (« le médecin voit ce qui n'est pas bouclé et ce qui traîne »), phase de
> conception validée le même jour : `Docs/specs/anneau-de-traitement/` (spécification § 6 et § 10, maquettes
> variante D, section 5). Décisions acceptées : ancienneté en **compteur J+N** plutôt qu'en cernes (14), seuils par
> catégorie réglés **au niveau de la boîte** (5, 8), **heures** pour une valeur critique (16), date de référence =
> ouverture de la boucle, jours calendaires (13), un réglage d'affichage par élément (17).

## Objectif

Une boucle ouverte montre **depuis combien de temps** elle l'est. Passé un premier seuil, la ligne affiche « J+N » ;
au dernier seuil, la boucle est **en retard** et le compteur passe en fond plein. Les seuils sont ceux de la boîte.
Chaque personne règle ce qu'elle veut voir, et une **légende** dessinée par le composant réel explique chaque signe.

### Ce qui est établi

Lecture du code au 2026-11-27 :

- **Aucune notion d'ancienneté, de retard ou d'échéance** n'existe dans `api-mail` ni dans les clients.
- **La date d'arrivée réelle** est sur la ligne : `MailDto.ArrivalDate` (task-466).
- **« Remettre à traiter »** date son geste : `MailHandlingStates.At`, rendu par `MailDto.Handling.At`.
- **Réglage de boîte, modèle à suivre** : la date de début du suivi (`MailboxTrackingStart`,
  `GET|PUT api/v1/account/mailboxes/current/tracking-start`, acte `MailboxTrackingStartChanged` tracé avec l'ancienne
  et la nouvelle valeur ; toute personne rattachée à la boîte peut la changer).
- **Réglages de la personne** : `UserSettingsDto`, sauvegardé en entier par les deux clients.
- **Écrans de réglages** : weda2 `libs/mss/src/features/settings/mss-settings.component.html` (sections « Lecture »
  avec cartes illustrées, « Boîte aux lettres » avec la date de suivi) ; mobile `src/app/settings/settings.page.html`
  (section « Suivi »). Aucune légende n'existe.
- **L'anneau et ses pastilles** sont posés par task-497.

### Règles

1. **Date de référence** d'une boucle ouverte : sa date d'arrivée réelle ; si le message a été remis à traiter, la
   date de ce geste.
2. **Catégorie** d'une boucle, pour ses seuils :
   - **biologie critique** : un compte rendu à valeur critique est à acquitter ;
   - **biologie** : un compte rendu avec anomalie est à acquitter ;
   - **courrier** : tout le reste.
3. **Seuils par défaut**, trois par catégorie, strictement croissants :

   | Catégorie | 1er seuil | 2e seuil | En retard |
   |---|---|---|---|
   | Biologie critique | 4 h | 24 h | 72 h |
   | Biologie | 1 j | 3 j | 7 j |
   | Courrier | 3 j | 7 j | 14 j |

4. **Les seuils appartiennent à la boîte.** Toute personne rattachée et active peut les changer, comme la date de
   début du suivi. Valeurs entières, strictement croissantes dans une catégorie, de 1 à 720 heures et de 1 à 365
   jours ; un refus est expliqué en français sous le champ. Chaque changement est **tracé** au nom de son auteur réel,
   avec les anciennes et les nouvelles valeurs.
5. **Compteur.** À partir du 1er seuil, la ligne affiche « J+N », N étant le nombre de jours entiers écoulés. Pour la
   biologie critique : « H+N » en heures jusqu'à 72 heures, « J+N » au-delà. Au dernier seuil, le compteur passe en
   **fond plein** et le libellé de l'anneau ajoute « en retard ». Avant le 1er seuil, rien ne s'affiche.
6. **Calcul à l'affichage.** L'ancienneté se calcule sur le poste, à partir de la date de référence et des seuils lus
   une fois avec les réglages. **Aucune écriture périodique en base**, aucun champ d'ancienneté stocké.
7. Un anneau fermé ou hors suivi n'affiche jamais d'ancienneté.
8. **Détail** : le bloc de l'anneau dit « Ouvert depuis N jours », et « en retard » au dernier seuil.
9. **Préférences de la personne**, toutes actives par défaut : affectation (initiales, « Non affecté »), attente
   d'un tiers, gravité, ancienneté, animations. Plus « Contraste renforcé », inactif par défaut (traits plus épais et
   plus sombres ; le contraste par défaut est déjà conforme). La couleur de gravité masquée laisse le badge
   d'acquittement ⚠ existant : une anomalie à acquitter reste toujours visible.
10. **Légende.** Une page « Légende des anneaux » dessine chaque état avec le **composant réel** : étapes, boucle
    fermée, hors suivi, initiales (collègue, soi, accès retiré), « Non affecté », attente d'un tiers, gravité,
    compteur. Elle cite les **seuils en vigueur** de la boîte et suit les préférences de la personne. Elle dit que les
    messages « Pour info », les accusés et les messages antérieurs au suivi n'ouvrent pas de boucle.
    - weda2 : section « Anneau de traitement » des Paramètres, après « Lecture » ; les seuils dans « Boîte aux
      lettres », à côté de la date de suivi.
    - Mobile : entrée « Anneau de traitement » des Paramètres, qui ouvre une page ; les seuils dans « Suivi ».

### Hors périmètre

- Les compteurs « en retard » du tableau de bord et le filtre de liste « En retard » : task-499.
- Les messages envoyés et leur seuil : non retenus (décision 9).
- Des règles par personne pour classer un message « sans action attendue » : non retenues (décision 1).

## Definition of Done

- [ ] Build passes : api-mail, dtos-mss, `nx build weda2`, client-mobile (0 erreur).
- [ ] Tests pass : api-mail, `nx test mss-lib`, `nx test weda2`, client-mobile (0 échec).
- [ ] Tests unitaires (api-mail) de la validation des seuils : valeurs par défaut sans ligne en base ; non croissants,
      nuls, négatifs, au-delà des bornes (refusés, message en français) ; chacun vu rouge.
- [ ] Test d'intégration de bout en bout pour la lecture et l'écriture des seuils de la boîte : sans réglage, la
      lecture rend les valeurs par défaut de la règle 3 ; après écriture, la lecture rend les nouvelles valeurs,
      relues dans la réponse réelle et en base. Cas d'échec : seuils non croissants → 400 en `problem+json`, rien
      d'écrit. Vu rouge (règle 1b).
- [ ] Test d'intégration en boîte partagée (règle 14) : le délégataire change un seuil ; le titulaire relit les
      seuils et obtient la nouvelle valeur ; la trace porte le délégataire en auteur, son rôle, l'ancienne et la
      nouvelle valeur. Vu rouge.
- [ ] Test d'intégration : les réglages d'affichage de la personne sont rendus et retenus, et ne sont **pas** partagés
      avec une autre personne de la même boîte. Vu rouge.
- [ ] Migration des seuils en ajout seul : aucune donnée existante modifiée ni supprimée ; descente qui retire ce
      qu'elle a ajouté ; relue (règle 7c).
- [ ] dtos-mss : contrats ajoutés publiés, api-mail bumpé ; `python Tools/contracts/contract_impact.py check` sans
      impact non adapté.
- [ ] Tests unitaires du calcul d'ancienneté, weda2 et mobile, à horloge fixée, vus rouges : avant le 1er seuil
      (rien) ; au 1er, au 2e, au dernier seuil ; biologie critique en heures puis en jours au-delà de 72 h ; message
      remis à traiter (la date du geste commande) ; anneau fermé ou hors suivi (rien) ; seuils modifiés pris en compte.
- [ ] Tests de composant, weda2 et mobile, vus rouges : « J+N » et « H+N » sur la ligne, fond plein et « en retard »
      dans le libellé au dernier seuil ; chaque préférence masque son élément et lui seul ; la gravité masquée laisse
      le badge ⚠ ; contraste renforcé ; la légende reprend les seuils de la boîte et les préférences.
- [ ] Aucune écriture périodique : aucun job, aucune colonne d'ancienneté (relu en revue).
- [ ] `data-testid` sur le compteur, chaque champ de seuil, chaque préférence et chaque entrée de légende ; aucun
      texte en dur hors de la convention de chaque client.
- [ ] Mobile : références Stitch des écrans `settings` et de la page de légende créées ou mises à jour
      (`/stitch-design`, best-effort).
- [ ] Scénario **E2E-RING-004** (version 1, `mobile: requis`, `angular: requis`) ajouté à
      `Api/Mail/e2e/scenarios.yml` et implémenté dans les deux clients : le test dépose un courrier à traiter arrivé
      il y a 8 jours et un autre arrivé aujourd'hui. Avec les seuils par défaut, le premier porte « J+8 », le second
      rien. Le praticien règle les seuils du courrier à 2, 5 et 8 jours : relus du serveur, ils sont enregistrés, et
      la ligne porte « J+8 » en fond plein avec « en retard » dans son libellé.
- [ ] Scénario **E2E-SETTINGS-006** (version 1, `mobile: requis`, `angular: requis`) : le praticien ouvre la légende ;
      elle montre les états et cite les seuils de la boîte. Il désactive « Ancienneté » : le compteur disparaît de la
      liste ; après rechargement, le choix est retenu ; il le réactive.
- [ ] Aucune donnée de santé dans les journaux ni dans la trace du changement de seuils (elle ne porte que des
      nombres).

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil de développement habituel).
- weda2 : `cd Client/Angular/front && npm run start:weda2`. Mobile : `cd Client/Mobile && npm start`.
- Données : une boîte partagée avec un délégataire ; un courrier à traiter arrivé il y a plus de 14 jours, un autre
  il y a 4 jours, un autre aujourd'hui ; un compte rendu de biologie à valeur critique arrivé il y a quelques heures.
- Référence visuelle : `Docs/specs/anneau-de-traitement/maquettes.html`, variante D, sections 2 et 5.

1. weda2, Boîte de réception : le courrier de 4 jours porte « J+4 » ; celui de plus de 14 jours porte son compteur en
   fond plein, et son libellé au survol dit « en retard » ; celui du jour ne porte rien. La biologie critique porte
   « H+N ».
2. Marquer « Traité » le courrier en retard : le compteur disparaît. « Remettre à traiter » : le compteur repart de
   zéro.
3. Paramètres, « Boîte aux lettres » : passer le 1er seuil du courrier à 5 jours ; « J+4 » disparaît de la liste.
   Saisir des seuils non croissants : refus expliqué sous le champ.
4. Se connecter en délégataire : les seuils sont ceux que le titulaire a réglés. Journal d'audit : le changement est
   au nom du titulaire, avec l'ancienne et la nouvelle valeur.
5. Paramètres, « Anneau de traitement » : la légende dessine chaque état et cite les seuils de la boîte. Désactiver
   « Ancienneté » : plus de compteur dans la liste, la légende le reflète. Le délégataire, lui, le voit toujours.
6. Activer « Contraste renforcé » : traits plus épais et plus sombres.
7. Refaire 1 à 6 sur le mobile.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du cabinet).
- **Vague Ségur** : hors Ségur — aide à l'organisation du cabinet, aucune exigence DSR nouvelle.
- **Exigences DSR honorées** : non applicable.
- **INS** : non applicable — aucun patient identifié ni manipulé.
- **Authentification PS** : inchangée — session PSC (e-CPS) de la messagerie.
- **Habilitations** : toute personne rattachée à la boîte et active (titulaire, membre, délégataire) lit et change les
  seuils, comme la date de début du suivi ; sans verdict récent de l'opérateur, ni lecture ni écriture (règle 14).
- **Interop CI-SIS** : non applicable. La catégorie « biologie critique » reprend le code d'interprétation posé par le
  laboratoire.
- **Tracé PGSSI-S** : un acte nouveau, **changement des seuils d'ancienneté de la boîte**, tracé au nom de la personne
  réelle (RPPS, nom PSC, rôle, boîte, instant, anciennes et nouvelles valeurs), conservé comme le changement de la
  date de suivi. Les réglages d'affichage de la personne ne sont pas tracés.
- **Consentement patient** : non applicable.
- **Référentiels métier** : aucun.
- **Hébergement HDS** : oui — les seuils sont une donnée de la boîte, dans sa base, environnement HDS existant ; les
  réglages d'affichage sont une donnée de la personne. Aucune donnée de santé nouvelle.
- **AIPD / impact RGPD** : inchangée — un réglage d'organisation, aucune donnée de santé ni décision automatisée.
