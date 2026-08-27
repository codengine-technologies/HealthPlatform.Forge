# todo-task-274.md — Chaque widget du tableau de bord a son interrupteur (feature flag)

**Repos**: client-blazor, client-angular, client-mobile
**Dependencies**: —
**Epic**: E015

## Objectif

L'arrivée sur le tableau de bord est le **geste le plus fréquent du parcours**
et le **deuxième poste du temps serveur** mesuré au banc (24,8 % au palier 1000,
campagne du 2026-08-26) — porté par plusieurs appels distincts (dossiers,
compteur du jour, couverture de synchro…). Aujourd'hui, impossible d'attribuer
la charge à un widget précis autrement que par instrumentation, et impossible
de **délester** en production si un widget se révèle coûteux.

**Intention** : chaque widget du tableau de bord est gouverné par un feature
flag Flagsmith. Flag OFF → le widget est **masqué ET son appel API n'est pas
émis** — c'est le point central : masquer sans couper l'appel ne changerait
rien à la charge, l'objectif est un interrupteur de charge, pas un interrupteur
d'affichage. Bénéfices : attribution de charge par activation/désactivation
sélective (pré-prod, banc en conditions réelles), et levier d'exploitation en
cas d'incident (délester le widget coûteux sans redéployer).

**Règles métier** (le cœur de l'US) :

1. **Fail-open, sans exception** : flag absent, Flagsmith injoignable, endpoint
   en erreur, réponse lente → **tout est visible**, comportement d'aujourd'hui.
   Un cabinet médical ne perd jamais un widget à cause d'un incident de
   configuration. Aucune erreur visible du praticien.
2. **Coût nul sur le geste** : la lecture des flags ne doit PAS ajouter un
   appel à chaque affichage du tableau de bord (ce serait aggraver le poste
   qu'on instrumente). Les flags sont lus **une fois par session applicative**
   (au démarrage de l'app ou à la connexion, via l'endpoint existant
   `GET /api/v1/FeatureFlag`), mis en cache côté client, rafraîchis au plus
   toutes les N minutes (N ≥ 5, choix d'implémentation documenté). Un
   changement de flag se propage donc en quelques minutes — c'est accepté,
   l'usage est l'investigation et le délestage, pas le temps réel.
3. **Convention de nommage imposée** : `dashboard_widget_{slug}` (kebab/snake
   du nom du widget), identique sur les trois fronts pour le même widget —
   c'est ce qui rend l'attribution lisible dans Flagsmith. La liste canonique
   couvre au minimum les appels mesurés au banc : compteurs de dossiers
   (`dashboard_widget_folders`), dossier principal/inbox
   (`dashboard_widget_folder_summary`), compteur du jour
   (`dashboard_widget_today`), couverture de synchronisation
   (`dashboard_widget_sync_coverage`). `/develop` inventorie les widgets
   réellement affichés par chaque front et **complète la liste** (un flag par
   widget affiché) ; l'inventaire final est consigné dans la task et repris
   dans le body des PRs pour que l'humain crée les flags dans Flagsmith.
4. **Les flags ne sont PAS créés par le code** : ils se créent dans
   l'administration Flagsmith (humain/exploitation). Le code se comporte
   correctement qu'ils existent ou non (règle 1). La US livre la **liste à
   créer**, pas la création.
5. **Un widget masqué ne laisse pas de trou** : la mise en page se recompose
   proprement (pas d'emplacement vide figé).

**Hors périmètre, dit explicitement** :
- Aucun changement `api-mail` : l'endpoint `FeatureFlagController` existant
  suffit ; aucun garde serveur par flag (couper l'appel côté client coupe la
  charge — un garde serveur dupliquerait la logique pour rien).
- Le harnais k6 (l'attribution au banc passe déjà par les probabilités
  `JOURNEY_*` par geste ; les flags servent l'attribution en conditions
  réelles et le délestage).
- Tout widget hors tableau de bord.

## Definition of Done

- [ ] Build + tests verts sur les trois fronts (`client-blazor`,
      `client-angular` code-only, `client-mobile`)
- [ ] Inventaire des widgets par front consigné dans la task (section
      `## Inventaire widgets/flags`), avec le nom de flag de chaque widget —
      convention `dashboard_widget_{slug}`, mêmes noms sur les trois fronts
- [ ] Flag OFF → le widget n'est pas rendu **et son appel API n'est pas émis**
      (test par front : composant/service avec flag coupé → zéro requête vers
      la route du widget)
- [ ] Flag absent ou lecture des flags en échec → tous les widgets visibles,
      aucun message d'erreur praticien (test du fail-open par front)
- [ ] La lecture des flags est faite au plus une fois par session applicative
      + rafraîchissement périodique — PAS à chaque affichage du dashboard
      (test : deux affichages successifs → une seule lecture des flags)
- [ ] Aucune chaîne en dur côté UI (i18n) pour tout libellé éventuel ;
      `data-testid` sur tout élément interactif ajouté
- [ ] Aucun changement de contrat d'API (l'endpoint FeatureFlag existant est
      consommé tel quel)

## Manual Test Plan

- Lancer le banc local : `cd Api/Mail && dotnet run --project src/AppHost --launch-profile https-load-test`
  (le conteneur Flagsmith du profil démarre avec lui), puis le front à tester
  (Blazor : `Client/Blazor` ; mobile : `cd Client/Mobile && npm start` ;
  Angular : selon la branche humaine).
- Dans l'admin Flagsmith du banc, créer `dashboard_widget_today` et le mettre
  **OFF**.
- Ouvrir le tableau de bord : le compteur du jour est absent, la mise en page
  est propre, et l'onglet Réseau (DevTools) **ne montre pas** l'appel
  `.../emails/today`.
- Remettre le flag **ON** : au prochain rafraîchissement de session (ou après
  le TTL), le widget revient et l'appel repart.
- Supprimer le flag / couper Flagsmith : tous les widgets visibles, aucun
  message d'erreur (fail-open).
- Vérifier qu'ouvrir deux fois le dashboard ne déclenche qu'une lecture des
  flags (Réseau : un seul `GET /api/v1/FeatureFlag` par session).

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — outillage d'exploitation/attribution de
  charge, aucun changement du contenu médical affiché quand les flags sont ON
  (état par défaut)
- **Exigences DSR honorées** : non applicable — aucun flux MSSanté modifié.
  ⚠️ Point de vigilance : si un widget porteur d'une obligation d'affichage
  (ex. acquittements de biologie, task-118 et suivantes) entre dans
  l'inventaire, son flag doit être documenté comme **outil d'incident
  uniquement** — le masquer en usage nominal dégraderait une exigence métier ;
  `/develop` le signale dans l'inventaire et le PO tranche flag par flag
- **INS** : non applicable — aucun traitement patient modifié
- **Authentification PS** : inchangée (l'endpoint FeatureFlag est derrière
  l'authentification existante)
- **Habilitations** : inchangées — les flags sont globaux (pas de ciblage par
  praticien dans cette US)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable côté produit (des booléens d'affichage,
  aucune donnée de santé) ; l'historique des changements de flags vit dans
  Flagsmith
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : inchangé — Flagsmith fait déjà partie de la plateforme
- **AIPD / impact RGPD** : néant — aucun nouveau traitement de données
