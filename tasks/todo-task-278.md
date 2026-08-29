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
