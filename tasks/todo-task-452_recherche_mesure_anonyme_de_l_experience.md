# todo-task-452.md — Recherche : mesure anonyme de l'expérience

**Repos**: api-mail, client-angular, client-mobile
**Dependencies**: done-task-445 (mode résultats weda2), done-task-450 (mode résultats mobile)
**Epic**: E023
**Priorité**: EPIC E023, demandée par l'humain le 2026-11-10. Règle d'or : mesurer avant d'améliorer. La refonte se
juge sur des chiffres, pas sur une impression.

> **Origine.** Analyse du 2026-11-10. Cible acceptée par l'humain : moins d'une seconde entre « Lancer » et l'affichage
> des résultats, squelette au-delà de 300 ms (task-445, task-450).

## Ce qui est établi

- Le serveur journalise la durée de chaque recherche (`ExecutionTimeMs`), sans indicateur agrégé exploitable.
- Rien ne mesure ce que vit le médecin : recherches sans résultat, nombre d'affinages, temps avant d'ouvrir un message.

## Objective

L'équipe produit suit, sur un tableau de bord, la qualité vécue de la recherche, sans jamais connaître ni ce qui a été
cherché, ni par qui.

Indicateurs, agrégés par jour et par client (weda2, mobile) :
- **Taux de recherches sans résultat** (aucun résultat exact).
- **Nombre d'affinages** avant l'ouverture d'un message ou la fermeture de la recherche (étiquette retirée, filtre
  ajouté, portée ou tri changés).
- **Temps avant ouverture** : du lancement de la recherche à l'ouverture d'un premier message (p50, p95).
- **Recherches abandonnées** : fermées sans qu'aucun message ne soit ouvert.
- **Durée vécue** : de « Lancer » à l'affichage des résultats, côté client (p50, p95), et durée côté serveur (p95).
- **Usage** : part des recherches utilisant un critère médical, une suggestion, la portée « Dossier courant », le tri
  « Les plus récents », « Sélectionner les N résultats ».

Règles :
- **Anonyme** : aucun terme, aucun critère en clair, aucun identifiant de personne, de patient ou de boîte dans les
  mesures. Seuls des compteurs et des durées, et le **type** des critères utilisés.
- **Corrélation** : les évènements d'une même recherche sont reliés par un identifiant de session de recherche
  aléatoire, sans lien avec la personne, oublié à la fermeture.
- **Seuil** : un tableau de bord signale quand le p95 de la durée vécue dépasse 1 seconde sur une journée.
- **Panne de mesure** : un envoi de mesure en échec ne gêne jamais le médecin (ni erreur, ni attente).
- Chaque réusultat de recherche doit affiché dans les logs serilog, le temps consomé afin de suivre la durée des traitement par logs

### Hors périmètre

- Les décisions tirées des chiffres : nouvelles tasks, à rédiger par `/po` sur les mesures.

## Definition of Done

- [ ] Build passes (0 errors) : `HealthPlatform.Api.Mail.sln`, weda2 (`nx build weda2`), client-mobile (`npm run build`)
- [ ] Tests pass (0 failures) : `HealthPlatform.Api.Mail.sln`, `nx test weda2`, `nx test mss-lib`, client-mobile
      (`npm test -- --watch=false --browsers=ChromeHeadless`)
- [ ] Tests unitaires du calcul des indicateurs (≥ 1 test par indicateur)
- [ ] **Test d'intégration de bout en bout (règle 1b)** sur la route de réception des évènements de recherche : une
      séquence lancer → affiner → ouvrir produit, lue dans les métriques exposées, 1 recherche, 1 affinage et un temps
      avant ouverture ; **aucun** terme, critère, identifiant de personne ou de boîte dans les données reçues ni
      exposées ; cas d'échec : un évènement mal formé → 400 en `ProblemDetails`, sans effet sur les compteurs ; vu rouge
      par mutation
- [ ] Test de composant dans les deux clients : un envoi de mesure en échec ne produit ni erreur ni attente à l'écran
- [ ] Tableau de bord des indicateurs ajouté au Grafana du projet, avec l'alerte p95 > 1 s ; capture dans le
      `## Develop log`
- [ ] Mesure de référence consignée : indicateurs relevés sur une session de recette (corpus fictif) avant la mise en
      service
- [ ] Aucune donnée de santé ni donnée personnelle dans les mesures et les logs (revue du schéma des évènements
      consignée)
- [ ] client-angular : code-only, aucun commit

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail/src/AppHost && dotnet run` ; weda2 : `cd Client/Angular/front && npm start` ;
   mobile : `cd Client/Mobile && npm start`.
2. Dans weda2 : rechercher `zorglubine` (aucun résultat), puis `psoriasis`, retirer une étiquette, ouvrir un message.
3. Sur le mobile : rechercher `catherine bernard`, fermer la recherche sans rien ouvrir.
4. Ouvrir le tableau de bord Grafana de la recherche : 1 recherche sans résultat, 1 affinage, 1 temps avant ouverture
   (weda2), 1 recherche abandonnée (mobile), et les durées vécues.
5. Inspecter les évènements reçus (Seq ou l'outil réseau du navigateur) : aucun terme, aucun nom, aucune adresse.
6. Couper la route de mesure : la recherche fonctionne sans erreur visible.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — pilotage produit
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — aucune donnée patient mesurée
- **Authentification PS** : inchangée — la route de mesure exige une session authentifiée (PSC, e-CPS), pour écarter les
  envois anonymes extérieurs ; l'identité n'est pas conservée dans les mesures
- **Habilitations** : non applicable — mesures agrégées, sans accès aux données de la boîte
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable — les mesures ne sont pas des actes sur la boîte ; les recherches restent tracées
  par `MailSearch`
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — les mesures ne contiennent aucune donnée de santé ni donnée personnelle
- **AIPD / impact RGPD** : note RGPD à compléter : mesure d'usage anonyme, sans donnée personnelle, conservation alignée
  sur la rétention des métriques du projet
