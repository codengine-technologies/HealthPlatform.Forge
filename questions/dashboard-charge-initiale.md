# questions/dashboard-charge-initiale.md — l'arrivée sur le tableau de bord

> Écrit le 2026-09-15, à la suite d'un constat humain en débogage sur
> `client-angular` et du tir de référence `journey` 500 praticiens du même jour.
> **Deux arbitrages produit sont demandés.** Le symptôme immédiat est déjà
> corrigé (`2957e621`) — ce qui suit ne l'est pas.

## Le constat

En ouvrant le tableau de bord pour la première fois, deux exceptions se
produisent systématiquement :

```
OperationCanceledException   ← à CancellationToken.ThrowIfCancellationRequested()
                               dans Npgsql.PoolingDataSource.RentAsync
NpgsqlException              ← « The connection pool has been exhausted,
                               either raise 'Max Pool Size' (currently 2) »
```

La seconde explique la première. Les requêtes attendaient une connexion Postgres
sur un pool de 2 ; l'une a dépassé les 15 s, l'autre a été abandonnée par le
client pendant l'attente (`takeUntilDestroyed`, hygiène Angular correcte).

**Le plafond de 2 était une borne du banc de charge appliquée par erreur au mode
nominal.** Corrigé : le mode développement passe à 10 par réplica, le chemin du
banc garde son 2, validé par la mesure. C'est un correctif de symptôme.

## Ce que le symptôme cachait

Le tableau de bord émet **14 appels API au premier rendu**, répartis sur
7 widgets :

| Widget | Appels |
|---|---|
| `mail-widget` | `getFolders`, `getFolder`, `getFolderToday` |
| `mail-notification-widget` | `getRecentUnread`, `getFolderNotSeenToday`, `getEmails`, **`enrichEmailsSync`** |
| `sync-progress-widget` | `getConnectionStatus` → `getUserSettings` → `getSyncStatus` (**en cascade**), `getSyncCoverage` |
| `offline-status-widget` | `getPendingEmails` |
| `biology-ack-pending-kpi-tile` | `getBiologyAckPendingSummary` |
| `abnormal-biology-widget` | `getAbnormalUnread` |
| `patient-widget` | `getPatientsWithUnreadMails` |

Ce n'est pas nouveau et c'est chiffré : le rapport du 2026-08-04 notait déjà que
l'arrivée sur le tableau de bord est **verte au SLO** tout en consommant **23 %
du temps serveur**, parce qu'elle émet plusieurs appels à chaque passage. Le tir
de référence du **2026-09-15** la donne à **39,8 %** — premier poste après la
recherche. Le SLO ne la voit pas : c'est un coût, pas une attente.

Une garde existe déjà (task-274) : chaque widget est derrière un drapeau, et
`flagsReady()` empêche d'instancier un widget avant que les drapeaux soient lus —
précisément pour éviter les requêtes émises puis annulées. Elle ne couvre pas ce
cas-ci : le widget n'est pas éteint par un drapeau, il est détruit **pendant
qu'il attend**.

---

## ARBITRAGE 1 — l'analyse CDA doit-elle rester sur le chemin du médecin ?

`mail-notification-widget` appelle **`enrichEmailsSync`** au chargement du
tableau de bord. C'est l'analyse CDA, en **synchrone**, dans la requête.

**Ce que ça coûte, mesuré** (tir de référence 500 praticiens, 2026-09-15) : un
lot d'analyse a coûté **4 896 ms en moyenne**, 60 s au pire cas. C'est ce qui a
fait tomber la chauffe du banc de 100 % à 90,4 % — 52 lots ont dépassé leur
délai.

> ⚠️ **Réserve de lecture.** La chauffe analyse par lots en rafale, à un rythme
> qu'un médecin ne produit jamais. Ces 4 896 ms sont un coût **de lot sous charge
> de chauffe**, pas la seconde qu'un médecin attend sur un message. Et le pire cas
> à 60 006 ms est exactement le plafond de temporisation du harnais : c'est une
> troncature, pas une mesure.

**Le fait le plus troublant** : l'API expose **deux** chemins qui font
exactement le même travail —

| Endpoint | Comportement |
|---|---|
| `enrich/async` | met en file (`IBackgroundTaskQueue`), rend `202 Accepted` — le médecin n'attend pas |
| `enrich/sync` | fait le travail en ligne — le médecin attend |

— et **aucun client n'emprunte le chemin en file**. Vérifié sur les trois fronts :

- **Angular** : `enrichEmailsSync` appelé à 3 endroits ; `enrichEmailsAsync` est
  **définie et jamais appelée** (elle n'apparaît que dans des artefacts de build).
- **Blazor** : `EnrichEmailsSyncAsync` dans le widget de notification.
- **Mobile** : `enrich/sync`.

**Un chemin non bloquant a été construit, et personne ne l'emprunte.** Soit il est
mort et il faut le retirer, soit c'est la bonne réponse et il faut l'adopter.

### Ce que « l'adopter » implique vraiment

Ce n'est **pas** un échange d'URL. En file, le client doit apprendre que
l'enrichissement est arrivé — SSE, sondage, ou rafraîchissement — sinon le
médecin voit une liste qui ne se remplit jamais. Et il faut décider ce qu'il voit
**pendant** : un indicateur de traitement, ou le message non enrichi ?

### ❓ Question au PO

**Le médecin doit-il attendre l'analyse CDA à l'ouverture du tableau de bord, ou
le tableau de bord doit-il s'afficher immédiatement et se compléter ensuite ?**

Et si c'est la seconde : **que voit le médecin pendant ce temps ?**

### ⚠️ Préalable technique que je recommande avant de trancher

Savoir **où** partent ces 4 896 ms : la part du service d'embeddings (externe)
contre la part IMAP et parsing (interne). Sans ça, basculer en file déplacerait
l'attente sans savoir ce qu'on déplace — et si la cause est externe, la file
traite le ressenti sans traiter le coût. La contre-épreuve est le même tir avec
l'indexation sémantique désactivée.

---

## ARBITRAGE 2 — la cascade sérielle du widget de synchronisation

`sync-progress-widget` enchaîne **trois allers-retours qui s'attendent** :

```
getConnectionStatus()  →  puis  getUserSettings()  →  puis  getSyncStatus()
```

Chaque maillon attend le précédent. Les deux premiers ne servent qu'à décider
s'il faut faire le troisième : hors ligne, on s'arrête ; synchro complète
désactivée, on s'arrête.

C'est la pire forme pour une page d'arrivée : on **additionne** les latences au
lieu de les paralléliser, et chaque maillon peut faire la queue sur le pool. Ce
widget est celui des deux exceptions du constat.

### ❓ Question au PO

**Est-ce qu'on accepte une US pour que le tableau de bord réponde en un seul
aller-retour par widget ?** Deux formes possibles, à arbitrer :

1. **Un endpoint d'arrivée** qui rend en une fois ce dont le tableau de bord a
   besoin. Le plus efficace ; couple le back à la composition de l'écran.
2. **Paralléliser** ce qui est indépendant et ne garder en cascade que ce qui
   dépend vraiment du résultat précédent. Moins de gain, aucun couplage.

---

## Ce qui n'est PAS demandé ici

- Le correctif de pooling : **déjà fait** (`2957e621`).
- Les drapeaux par widget : **déjà en place** (task-274). Éteindre des widgets
  est un contournement, pas une réponse — la question est ce que coûte un widget
  allumé.
- La recherche sémantique : rouge au tir de référence (p95 26 691 ms, 35,5 % du
  temps serveur), mais c'est un **sujet distinct**, déjà rouge au 2026-09-08 et
  imputé alors à 67 % au service externe. Elle mérite sa propre US.
