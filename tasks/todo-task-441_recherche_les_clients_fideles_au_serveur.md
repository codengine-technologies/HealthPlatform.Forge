# todo-task-441.md — Recherche : les clients fidèles au serveur

**Repos**: client-angular, client-mobile, api-mail
**Dependencies**: done-task-440 (contrat des groupes et des sections ; 438 et 439 sont requises en amont)
**Epic**: E022
**Priorité**: EPIC E022, demandée par l'humain le 2026-11-09. Les deux clients doivent montrer au médecin ce que le
serveur a trouvé, dans l'ordre et avec les avertissements du serveur, et la même chose dans weda2 et sur le mobile.

> **Origine.** Campagne du 2026-11-09 : `Docs/audits/recherche-campagne-bugs-weda2-mobile-20261109.md`, défauts **R7**
> (part client), **R8**, **R9**, et les défauts lus dans le code (section « non exercés »). Analyse des deux clients :
> même rapport. `api-mail` figure dans les Repos pour le catalogue e2e et ses seeds.

## Ce qui est établi

Lecture du code au 2026-11-09 (weda2 : `Client/Angular/front/libs/mss/src` ; mobile : `Client/Mobile/src/app`) :

| Défaut | weda2 | Mobile |
|---|---|---|
| **R8 ordre** | garde l'ordre du serveur | **retrie par date d'envoi** (`features/mail/services/mail-state.service.ts`, l.103-104) : pour `psoriasis`, les 6 bons résultats passent des rangs 1-6 aux rangs 5, 42, 44, 48, 49, 50 |
| **R9 avertissements** | `search.model.ts` n'a ni `hits`, ni `isTruncated`, ni `isDegraded`, ni `degradedSources` : rien n'est montré | idem |
| Résultats rattachés | par **UID dans le dossier courant** ; le dossier de chaque `hit` est ignoré | idem |
| Aucun dossier sélectionné | la recherche porte sur tous les dossiers, mais `mail-list.component.ts` (l.698) abandonne l'affichage sans dossier (à confirmer à l'écran) | envoie INBOX |
| Requête dépassée | annulée (`switchMap`) | **non annulée** (`mail-search.component.ts`, l.267-282) : une réponse lente peut écraser la plus récente |
| Erreur | **rien n'est affiché**, l'ancienne liste reste (l.579-582) | message du serveur affiché ; un échec du chargement des en-têtes affiche « Erreur de recherche » (`HttpErrorResponse` n'est pas une `Error`, page l.59) |
| Réglage de similarité | réglage de la personne (écran Paramètres) | stockage local (`search-settings.service.ts`) |
| Pages | pages côté client sur les 50 premiers | les 50 d'un coup, sans suite |

Après task-439 et task-440, le serveur rend des **groupes** (tous les mots / une partie des mots), une section
**proches**, une **page suivante**, et ignore le seuil envoyé par le client.

## Objective

Dans weda2 comme sur le mobile, le médecin voit ce que le serveur a trouvé, dans l'ordre du serveur, avec ses
avertissements, et peut aller jusqu'au dernier résultat. Les deux clients se comportent de la même façon.

Règles :
- **L'ordre du serveur est l'ordre affiché** : plus aucun tri par date sur les résultats d'une recherche.
- **Trois parties visibles**, chacune titrée, dans l'ordre : « Tous les mots », « Une partie des mots », « Résultats
  proches ». Une partie vide n'est pas affichée. Pour un mot absent : « Aucun résultat » (et les proches, s'il y en a).
- **Aller jusqu'au bout** : quand la réponse est tronquée, « Voir plus » demande la page suivante au serveur, jusqu'au
  dernier résultat.
- **Panne signalée** : quand un moteur est en panne (`isDegraded`), un message dit que les résultats peuvent être
  incomplets.
- **Erreur affichée** : en cas d'échec, un message clair ; l'ancienne liste n'est jamais laissée à l'écran comme si
  elle était le résultat de la nouvelle recherche.
- **Requête dépassée abandonnée** dans les deux clients : seule la réponse à la dernière recherche s'affiche.
- **Chaque résultat est rattaché par son dossier et son UID** (les `hits`), y compris dans un dossier d'étiquette et
  quand aucun dossier n'est sélectionné.
- **Plus de réglage de similarité** dans l'interface des deux clients (le serveur décide, task-440). Les valeurs
  enregistrées sont ignorées.
- **Mêmes libellés** et même comportement dans les deux clients ; libellés en français, sans donnée de santé.

### Hors périmètre

- La logique de recherche côté serveur : tasks 439 et 440.
- La recherche avancée par filtres et la recherche de patients (`Patients/search`) : inchangées.

## Definition of Done

- [ ] Build passes (0 errors) : weda2 (`nx build weda2`), client-mobile (`npm run build`)
- [ ] Tests pass (0 failures) : `nx test weda2`, `nx test mss-lib`, client-mobile (`npm test -- --watch=false --browsers=ChromeHeadless`)
- [ ] Tests de composant dans les deux clients : ordre du serveur conservé, trois parties titrées, « Voir plus »,
      message de panne, message d'erreur et liste vidée, réponse dépassée ignorée, rattachement par dossier et UID ;
      chacun vu rouge par mutation
- [ ] **Scénarios e2e** ajoutés à `Api/Mail/e2e/scenarios.yml`, mobile et Angular requis, implémentés dans les deux
      clients, vérifiant le **contenu** de la liste :
      - `E2E-SEARCH-004` v1 : un nom de patient tapé sans accent ni majuscule trouve ses messages, sous « Tous les mots »,
        puis les messages partiels sous « Une partie des mots » ;
      - `E2E-SEARCH-005` v1 : un mot absent de la boîte affiche « Aucun résultat » ;
      - `E2E-SEARCH-006` v1 : plus de résultats qu'une page : « Voir plus » affiche la suite, jusqu'au dernier ;
      - `E2E-SEARCH-007` v1 : une recherche en échec affiche un message, et l'ancienne liste n'est plus affichée ;
      - chacun vu rouge par mutation ; `E2E-SEARCH-001` à `003` restent verts
- [ ] Les requêtes de référence de task-438 marquées « task-441 », s'il y en a, sont vertes
- [ ] Réglage de similarité retiré de l'écran Paramètres de weda2 et du mobile ; aucune régression des autres réglages
- [ ] `data-testid` sur chaque élément interactif ajouté (titres de parties, « Voir plus », messages)
- [ ] Aucune chaîne en dur hors des conventions de libellés de chaque client ; aucune donnée de santé dans les libellés
- [ ] client-angular : code-only, aucun commit (l'humain gère la branche et TFS)
- [ ] **Prévention (règle d'or)** : consigne dans `conventions/angular.md` : un client ne retrie ni ne refiltre une
      liste ordonnée par le serveur, et lit tous les signaux de la réponse (`isTruncated`, `isDegraded`, `hits`)

## Manual Test Plan

1. Lancer le backend sur la boîte de formation de Virginie : `cd Api/Mail/src/AppHost && dotnet run`. Lancer weda2
   (`cd Client/Angular/front && npm start`) et le mobile (`cd Client/Mobile && npm start`).
2. Dans les deux clients, avec la CPS de Virginie, rechercher :
   - `catherine bernard` : « Tous les mots » en tête, puis « Une partie des mots » ; « Voir plus » jusqu'aux plus
     anciens messages de Catherine BERNARD ;
   - `psoriasis` : les 6 messages, dans le même ordre dans les deux clients ;
   - `zorglubine` : « Aucun résultat ».
3. Couper le serveur pendant une recherche : un message d'erreur s'affiche, l'ancienne liste disparaît.
4. Taper vite une recherche puis une autre sur le mobile : seule la dernière s'affiche.
5. Ouvrir un dossier d'étiquette, rechercher : chaque résultat ouvre le bon message.
6. L'écran Paramètres ne propose plus de réglage de similarité.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (messagerie MSSanté du praticien)
- **Vague Ségur** : hors Ségur — fiabilité de la recherche
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — aucun identifiant patient affiché par la recherche
- **Authentification PS** : inchangée — PSC (e-CPS), niveau eIDAS substantiel
- **Habilitations** : inchangées — verdict de l'opérateur MSSanté (règle 14)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : inchangé — chaque recherche et chaque page suivante tracées côté serveur (`MailSearch`) au nom de
  la personne réelle, 3 653 jours
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non applicable aux clients — aucune donnée stockée ; le mobile ne garde plus de réglage de
  similarité
- **AIPD / impact RGPD** : inchangé
