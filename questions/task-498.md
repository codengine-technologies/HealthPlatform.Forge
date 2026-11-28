# task-498 — /e2e rouge : l'ancienneté lit les dates du serveur comme des heures locales

**Étape** : `/e2e` (voie mobile). **Nature du blocage** : **régression** sur un parcours nouveau de la task
(E2E-RING-004), causée par un défaut du code de la task. Ni parité ni outillage.

## Ce qui a rougi

- Voie mobile : E2E-RING-004 rouge aux deux essais, sur sa prémisse « arrivé il y a 8 jours » : `calendarDaysAgo` rend
  **9**. E2E-SETTINGS-006 a vu « J+9 » au lieu de « J+8 » au premier essai, puis est passé au second.
- Voie Angular : verte (110), parité verte. Elle a tourné **après** minuit UTC.

## Cause

- api-mail stocke `ArrivalDate` et `SentDate` en `timestamp without time zone` : l'instant UTC, relu par Npgsql en
  `DateTimeKind.Unspecified`, sérialisé **sans `Z`** (`"2026-11-19T23:50:00"`).
- Le calcul d'ancienneté des deux clients (mobile `treatment-ring-aging.util.ts`, weda2 `mail-aging.util.ts`) et le
  helper e2e `calendarDaysAgo` font `new Date(chaîne)` : une chaîne sans fuseau est lue comme une heure **locale**.
- Conséquences produit, sur les deux clients :
  - entre minuit local et minuit UTC (00 h-01 h l'hiver, 00 h-02 h l'été), le compteur « J+N » a un jour de trop ;
  - le compteur « H+N » de la biologie critique a une heure de trop (deux l'été), **à toute heure** ;
  - « Ouvert depuis N heures » du détail, idem.
- Les tests unitaires ne l'ont pas vu : leurs jeux de données portent des dates avec `Z`.

## Correctif proposé (borné, corrigeable par la forge)

Reprise `/develop task-498 --reprise` avec un seul constat **B-E1** :
1. Dans les deux clients, la lecture d'une date du serveur pour l'ancienneté traite une chaîne ISO **sans désignateur de
   fuseau** comme UTC (ajout de `Z`), une chaîne avec `Z` ou un décalage restant inchangée.
2. Tests unitaires vus rouges : date `"2026-11-19T23:30:00"` (sans `Z`) lue à `2026-11-28T00:30` heure de Paris →
   J+8 (rouge aujourd'hui : J+9) ; biologie critique `"…T09:00:00"` à 11 h 00 heure de Paris → H+1 (rouge : H+2).
3. Helper e2e `calendarDaysAgo` des deux clients : même lecture.
4. Puis `/review --code` (boucle courte) et `/e2e` (voies complètes).

## Hors task, à signaler

Le même défaut de lecture touche **l'affichage** des heures de `sentDate` dans les clients, s'ils les affichent
sans conversion (décalage d'une à deux heures). C'est antérieur à task-498 et non vérifié ici : une task à part, après
vérification à l'écran.

## Décision attendue

Relancer la reprise : `/develop task-498 --reprise` (le constat B-E1 sera ajouté au `## Code Review Summary`), ou
trancher autrement.
