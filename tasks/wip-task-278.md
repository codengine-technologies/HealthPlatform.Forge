# todo-task-278.md — L'arrivée sur le tableau de bord coûte encore un tiers du temps serveur

**Repos**: api-mail
**Dependencies**: task-276 (recommandée avant : elle instrumente la fenêtre de verdict des verrous et tranche si la contention de session pèse sur ce geste — sans quoi cette US risquerait de re-désigner une cause déjà nommée ailleurs)
**Epic**: E015

## Objectif

L'arrivée sur le tableau de bord est le **geste le plus fréquent du parcours**
et reste le **premier poste du temps serveur**. Le tir du 2026-08-29
(`Api/Mail/tests/loadtest-k6/reports/2026-08-29/report-journey-500-task270-20260829-220155.md`,
finding **F-273-1**) le mesure inchangé :

| | Réf 26/08 | Tir 29/08 |
|---|---|---|
| Part du temps serveur | 35,0 % (8 262,0 s) | **34,9 %** (8 243,3 s) |
| Appels | 66 532 | 66 852 |
| Moyenne / p95 | 124 / 557 ms | 123 / 559 ms |
| Dispersion p95/p50 | — | **40,2×** |

**Deux critères de clôture posés par des US antérieures ne sont pas atteints**,
et c'est ce qui rouvre le chantier :

- task-273 (réduite à son filet d'intégration après le merge de #205) laissait
  « part dashboard **< 15 %** au banc » au prochain tir → **34,9 %**.
- task-270 laissait « `dashboard,call:folder` p95 **< 500 ms** au palier 500 et
  part du dashboard **< 18 %** » → **928 ms** et **34,9 %**.

**Le résultat le plus utile de ce tir est négatif, et il oriente cette US.**
task-270 a retiré 2 allers-retours IMAP sur 7 pour un cache-miss — mécanisme
prouvé par le compteur de sollicitations — et le coût de l'appel `folder` n'a
**pas bougé** (moyenne 357,1 → 358,4 ms, +0,4 %). Autrement dit :

> **Le coût de l'arrivée dashboard n'est PAS gouverné par le nombre
> d'allers-retours IMAP.** C'est mesuré, pas supposé. Cette piste est fermée.

### ⚠️ La cause n'est PAS établie — l'établir fait partie de l'US

Cette EPIC a déjà annulé une US écrite sur une cause supposée (task-222), et
task-270 vient d'illustrer le coût de l'autre erreur : une cause **réelle mais
non gouvernante**. **Aucune ligne de remède ne s'écrit avant que la cause soit
établie sur pièce.**

Faits disponibles pour démarrer, ventilation par appel du geste (palier 500,
ce tir) :

| Appel | n | moyenne | p50 | p95 | Lecture |
|---|---|---|---|---|---|
| `folder` | 16 713 | **358,4 ms** | 140,3 | 928,3 | porte le geste ; **insensible aux allers-retours** (task-270) |
| `today` | 16 713 | 85,4 ms | **8,1** | 379,2 | p95/p50 = **47×** — coût bimodal, pas fixe |
| `folders` | 16 713 | 42,5 ms | 16,3 | 142,6 | — |
| `coverage` | 16 713 | 6,9 ms | 4,3 | 14,1 | négligeable |

Pistes **non tranchées**, à instruire avant d'en retenir une :

1. **Contention de session** — `imap_session` sérialise toutes les opérations
   IMAP du praticien ; la détention de la lecture de dossier atteint 11,871 s au
   p95 (F-270-1). C'est **task-276** qui doit dire si cela vit en régime ou en
   chauffe. Si oui, une part du coût du dashboard est déjà adressée là — et
   cette US doit chercher ailleurs.
2. **Coût par appel indépendant de la charge** — le p95 de `folder` était
   **plat** de 100 à 500 médecins avant task-270 (696 → 699 → 698 ms) : signature
   d'un coût fixe par appel, que ni la population ni les allers-retours
   n'expliquent.
3. **Le geste émet 4 appels à chaque passage** — 66 852 appels d'étape pour
   16 713 arrivées. La question « faut-il 4 appels ? » n'a jamais été posée
   comme telle. task-274 a livré les interrupteurs par widget : **le banc peut
   désormais éteindre un widget et mesurer ce qu'il coûtait réellement** —
   c'est l'instrument d'attribution qui manquait.

**Piste explicitement recommandée** : se servir des flags `dashboard_widget_*`
(task-274) pour **attribuer la charge par activation/désactivation sélective**
au banc, avant tout remède. C'est exactement l'usage pour lequel ils ont été
créés, et il n'a encore jamais été exercé.

**Ce qui n'est PAS dans le périmètre** : le nombre d'allers-retours IMAP (piste
fermée par la mesure), le comportement fonctionnel du tableau de bord, la
suppression d'un widget (le PO tranche l'affichage, pas la forge).

## Definition of Done

- [ ] Build passes (0 erreur)
- [ ] Tests pass (0 échec)
- [ ] **La cause est établie et écrite** dans le task file, chiffres et méthode à
      l'appui — distinguer ce qui est **mesuré** de ce qui est **lu dans le code**
- [ ] L'attribution par widget a été exercée au banc via les flags
      `dashboard_widget_*` (task-274), et le coût de chaque appel du geste est
      chiffré séparément
- [ ] Si la cause désigne la contention de session : **ne rien réimplémenter
      ici**, renvoyer à task-276 et clore cette US sur le constat
- [ ] Si remède : tests unitaires sur chaque branche nouvelle
- [ ] Si remède : contrat de la route **inchangé** — parité champ pour champ du
      corps de réponse, testée
- [ ] Fraîcheur : tout TTL modifié est justifié au point de décision et fixé par
      un test (précédent task-270)
- [ ] Aucune donnée de santé dans les journaux ni dans les étiquettes de métriques

## Manual Test Plan

**Ce que l'humain valide au HAG** : que le tableau de bord affiche la même chose
qu'avant. Le gain est un fait de banc et se juge au tir suivant.

1. Lancer le banc :
   ```bash
   cd Api/Mail
   dotnet run --project src/AppHost --launch-profile https-load-test
   ```
2. Attendre `http://127.0.0.1:5052/api/v1/connection/status` en 200, puis
   seeder : `dotnet run --project tests/mss.mail.loadtest.seed -- --users 2 --messages 30 --api http://127.0.0.1:5052`
3. Ouvrir le tableau de bord du client Blazor et **relever les quatre valeurs
   affichées** (dossiers, compteur du jour, couverture de synchro, non-lus).
4. **Vérifier** : les quatre widgets affichent les mêmes valeurs qu'avant la
   modification, et une seconde arrivée dans la fenêtre de cache ne relance pas
   de recherche (journaux `[ListFolder]`).
5. **Attribution par widget** (l'instrument de l'US) : dans Flagsmith
   (`http://127.0.0.1:8000`, projet `HealthPlatform.Mss`), basculer
   `dashboard_widget_today_summary` à OFF, recharger le tableau de bord.
   **Vérifier** : le widget disparaît **et** l'appel `today` n'est plus émis
   (journaux serveur). Rebasculer à ON, le widget revient — fail-open confirmé.
6. **Clôture de l'US — au banc, tir suivant** : tir `journey` 500 médecins en
   iso-conditions du `report-journey-500-task270-20260829-220155.md`, sur la
   **même base hydratée**. Critères :
   - part de l'arrivée dashboard dans le temps serveur **< 25 %** (contre 34,9 %)
     — cible intermédiaire assumée, le < 15 % de task-273 n'ayant jamais été
     étayé par une cause
   - `dashboard,call:folder` moyenne **< 300 ms** (contre 358,4)
   - dispersion p95/p50 du geste **< 20×** (contre 40,2×)
   - 11/11 étapes toujours vertes, 0 mélange, taux d'erreur inchangé

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — optimisation de performance interne
- **Exigences DSR honorées** : non applicable — comportement fonctionnel inchangé
- **INS** : non applicable
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — IMAP interne au périmètre MSSanté existant
- **Tracé PGSSI-S** : inchangé — la consultation du tableau de bord reste journalisée à l'identique
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — inchangé
- **AIPD / impact RGPD** : inchangé

## Branches

- `api-mail` (pushed) : `feat/task-278-dashboard-cost`
- `dtos-mss` (pushed, auto-inclus) : `feat/task-278-dashboard-cost`
- `client-angular`, `client-mobile`, `devops`, `psc-proxy-*` — non concernés

## Develop log — CAUSE ÉTABLIE, remède non écrit (arbitrage produit requis)

**Aucun code de production n'a été écrit.** L'US exigeait d'établir la cause
avant tout remède ; la cause est établie, et le remède qu'elle appelle est une
**décision produit**, pas une décision technique. Voir `questions/task-278.md`.

Instruction menée sur les données Prometheus du tir du 2026-08-29, **sans
rejouer de tir**.

### 1. La piste des allers-retours est fermée — et bien plus largement qu'on ne croyait

Le compteur de sollicitations et la table des verrous permettent de reconstituer
le mélange froid/chaud des **deux** tirs :

| | 26/08 (avant task-270) | 29/08 (après) | Δ |
|---|---|---|---|
| lectures de dossier /s | 11,51 | 11,83 | volume identique |
| recherches complètes /s | 7,22 | **2,95** | **−59 %** |
| **part froide** | **62,7 %** | **24,9 %** | — |
| **allers-retours IMAP /s** | **59,1** | **32,5** | **−45 %** |
| **coût moyen `call:folder`** | **357,1 ms** | **358,4 ms** | **+0,4 %** |

task-270 a livré **deux** gains cumulés — 7→5 allers-retours par miss, **et** la
part froide effondrée par son second remède (« reçus aujourd'hui » ne jette plus
une recherche encore valide). Ensemble : **45 % des allers-retours du chemin
dossier supprimés.** Le coût vu du médecin n'a pas bougé d'un millimètre.

> **Le coût de `GET /mail/folders/{name}` n'est pas borné par les allers-retours
> IMAP.** Établi deux fois, à une magnitude qui ne laisse aucune ambiguïté.

### 2. La cause : l'appel n'est pas cher, il est FROID — et il l'est par construction

Le harnais émet **la même route deux fois par itération**, à quelques secondes
d'écart, sur la même session :

| Appel | n | moyenne | p50 | p95 |
|---|---|---|---|---|
| `dashboard,call:folder` (1er de l'itération) | 16 713 | **358,4 ms** | **140,3** | 928,3 |
| `read_list,call:folder` (~5 s plus tard) | 16 722 | **52,7 ms** | **10,3** | 139,7 |
| **facteur** | — | **×6,8** | **×13,6** | ×6,6 |

Même route, même travail, même session, même dossier. **Le seul écart est la
position dans le parcours.** Reproduit à l'identique au tir de référence
(357,1 vs 43,8).

**Mécanisme** : un passage complet du médecin dure ~63 s. Entre la fin d'une
itération et l'arrivée dashboard de la suivante, **toutes les fenêtres de cache
ont expiré** (`folder:status` 10 s, `folder:uids` 5 min) — l'arrivée dashboard
est donc froide **par construction**. L'appel de l'inbox, lui, tombe 3-10 s plus
tard, dans la fenêtre de 10 s : il est chaud par construction.

C'est exactement la réconciliation que le dossier de cause de task-273 avait
écrite (« deux populations, pas deux coûts ») — cette instruction la **chiffre**
et prouve qu'elle survit à task-270.

### 3. Écart client/serveur — vérifié, et il n'y a rien

J'ai d'abord cru lire 185 ms d'écart. **C'était une faute de comparaison de ma
part** (moyenne client d'un seul des deux appels contre moyenne serveur des
deux). Recalculé proprement : client 205,5 ms sur les deux appels, serveur
172,9 ms → **32,6 ms**, l'ordre de grandeur d'un aller-retour localhost à travers
le proxy DCP. **Rien à chercher de ce côté.**

### 4. ⚠️ Ma propre recommandation de task file était fausse

Le task file recommandait d'« attribuer la charge widget par widget via les flags
`dashboard_widget_*` de task-274 ». **Ça ne marche pas au banc** : k6 appelle
l'API directement et ne lit jamais Flagsmith ; basculer un flag ne change donc
rien à la charge émise. Les flags restent un levier d'exploitation réel (front
réel, pré-prod), mais **pas un instrument de banc**. Consigné pour que personne
ne le retente.

### 5. Attente du verrou — mesurée, et significative

`ReadFolder` : attente **moyenne** du verrou de session **82,8 ms**, soit ~48 %
du temps serveur moyen de la route (172,9 ms). Ce n'est pas la cause du coût
froid, mais c'est un poste réel, et il grandira avec la population.

## Pourquoi la chaîne s'arrête ici

Le remède que la cause appelle est un **arbitrage de fraîcheur** : servir
l'arrivée dashboard depuis le cache et rafraîchir derrière, ou allonger la
fenêtre de statut. Les deux échangent de la **fraîcheur des compteurs affichés
au praticien** contre du temps. **Ce n'est pas une décision technique** — c'est
au PO de dire de combien de secondes un compteur de messages peut être périmé.

Règle 7 (fail-fast sur ambiguïté de règle métier) → `questions/task-278.md`.
