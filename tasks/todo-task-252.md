# todo-task-252.md — Télécharger une pièce jointe passe de 1 à 4,8 secondes entre 200 et 500 praticiens

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: **task-244** (chauffe) — la mesure de confirmation exige un tir
500 valide. La **première moitié** de cette US (établir la cause) n'attend rien.
**Priorité**: **2** — c'est le goulot **G2** du tir 500 : une étape verte à 100 et
200 qui sort franchement de la grille à 500, avec des abandons.

## Objective

Établir **pourquoi** le téléchargement d'une pièce jointe s'effondre entre 200 et
500 praticiens — puis seulement décider du remède.

⚠️ **US en deux temps, et l'ordre n'est pas négociable** : mesurer, puis corriger.
Cette EPIC a annulé une US applicative écrite sur une cause plausible et fausse
(task-222).

## Ce qui est établi

Tir `journey-remote-n500` du 2026-08-09, étape « Télécharger une PJ (~124 Ko) » :

| Palier | p50 | p95 (cible 2 000 ms) | Verdict |
|---|---|---|---|
| 100 médecins | — | dans la grille | ✅ |
| 200 médecins | — | dans la grille | ✅ |
| **500 médecins** | **573 ms** | **4 771 ms** | ❌ + **16 abandons** (HTTP 0) |

Le smoke comparatif local/cluster l'avait signalé à **+45 %** sur 6 échantillons
seulement — donc sans valeur probante à ce stade ; le tir le confirme sur **5 162**.

**Ce qui est déjà écarté** : ce n'est pas un plafond matériel. Aucune ressource
n'est épinglée sur ce tir (CPU maximal **8,3 % de 24 cœurs**, file ThreadPool
calme, RSS plate). Le plafond est dans une **dépendance sérialisée**.

**Une réserve de méthode à porter dans l'analyse** : ce tir tournait sur une base
quasi vide (chauffe échouée), donc le chemin base est sous-sollicité. Cela **ne
disqualifie pas** ce constat — le téléchargement d'une PJ est un chemin **IMAP**,
peu dépendant du contenu de la base — mais il faudra le reconfirmer sur un tir à
chauffe réussie.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que c'est le NFS du cluster.** C'est le candidat commode. Le
  smoke a mesuré la lecture froide IMAP à **+6 %** seulement entre local et
  cluster : le stockage distant ne dégradait pas les lectures à faible charge. À
  500, c'est peut-être différent — mais il faut le **mesurer**, pas le supposer.
- **Ne pas présumer que c'est le verrou de session IMAP.** C'est le candidat
  historique de cette EPIC, et il a déjà été écarté une fois sur un autre chemin.
- **Ne pas présumer que c'est la taille.** 124 Ko à 94 ms de latence injectée ne
  font pas 4,8 s à eux seuls : il y a de l'attente quelque part, à localiser.

## Definition of Done

- [ ] La cause est **établie** par la télémétrie, pas supposée : décomposition
      d'une requête représentative (contexte, acquisition de session, fetch
      `BODY[part]`, streaming vers le client), avec les requêtes qui l'établissent
- [ ] Il est dit explicitement si la cause est **côté serveur mail** (Dovecot/NFS)
      ou **côté api-mail** — les deux remèdes n'ont rien à voir
- [ ] Les 16 abandons sont expliqués : côté client (délai) ou côté serveur
- [ ] Si un correctif est livré : A/B iso-conditions, un seul facteur, et l'étape
      rentre dans la grille au palier 500
- [ ] Si aucun correctif n'est livré : le **dire**, écrire pourquoi, et poser le
      seuil qui rouvrirait le sujet
- [ ] Ce que la télémétrie n'a **pas** pu dire est écrit — c'est le backlog
      d'instrumentation de la US suivante

## Manual Test Plan

- Monter le banc en mode distant, tir `journey` avec paliers 200 puis 500
- Pendant le palier 500, ouvrir un message et télécharger sa pièce jointe depuis
  l'application : le fichier doit arriver **complet et intègre** (l'archive
  IHE_XDM doit s'ouvrir), quelle que soit la latence
- Relever en parallèle le CPU des pods du cluster (`kubectl top pods`) pour
  distinguer un plafond serveur mail d'un plafond api-mail

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — performance
- **Exigences DSR honorées** : aucune exigence nouvelle ; ⚠️ la pièce jointe **est**
  le document clinique — une troncature silencieuse serait une perte de donnée de
  santé, et prime sur toute considération de performance
- **INS** : l'archive IHE_XDM porte des CDA avec INS — aucun contenu ni nom de
  fichier patient dans les journaux ou les étiquettes de métrique
- **Interop CI-SIS** : volet transport MSSanté / IHE-XDM — l'intégrité de l'archive
  est un critère **bloquant** de cette US
- **Habilitations** : un praticien ne doit pouvoir télécharger que les pièces de
  **ses** messages — à re-vérifier si le chemin de streaming est modifié
- **Authentification PS / Consentement** : inchangés
- **Tracé PGSSI-S** : inchangé
- **Hébergement HDS** : le verdict devra être transposable à la cible
- **AIPD / impact RGPD** : inchangé
