# questions/task-345.md — Un parcours rouge sur un défaut connu : corriger ici, attendre task-342, ou mettre en quarantaine ?

**Étape** : `/develop` (Step 6, vérification finale). **État** : tout le reste est fait et committé
(non poussé). La chaîne est arrêtée sur ce seul point, qui est une décision de périmètre.

## Constat

Le filet headless tourne de bout en bout : 4 runs complets, démontage propre à chaque fois, parité
catalogue ↔ suite **verte**. Dernier run (run 4) : **20 verts, 1 flaky, 1 rouge**.

| Scénario | Résultat | Cause |
|---|---|---|
| `E2E-BIO-001` — acquitter un compte rendu de biologie | ❌ rouge, reproductible | le détail du mail bio arrive **sans son document CDA** : pas d'onglet « Biologie », donc pas de panneau d'acquittement |
| `E2E-DETAIL-002` — bascule texte / HTML | ⚠️ flaky | au premier essai, le contenu du mail arrive sans corps |

**Les deux ont la même cause, et elle est déjà connue : AUD-27** (audit du 2026-09-27, lot C de
**task-342**) — « le cache `Mail.Email` fige la version d'avant l'analyse pendant 15 min ».

Mesure, sur un backend neuf :
- avant toute UI, `GET /emails/content/3` rend **1 document, 2 résultats de biologie** (chemin base) ;
- après l'affichage de l'inbox par l'app, le même appel rend **0 document et un `messageId` vide** —
  une réponse construite par le **repli IMAP**, puis **mise en cache 15 min** (`MailController.cs:650-667`,
  seul écrivain de cette clé). La base, elle, porte toujours le document (vérifié en SQL).

Pour un médecin, c'est le même symptôme : il ouvre un résultat de biologie juste après
l'affichage de la boîte, et pendant 15 minutes il ne voit ni le document, ni le panneau
d'acquittement.

## Arbitrage humain requis

1. **(a) Corriger AUD-27 ici**, dans task-345. Le remède de l'audit tient en peu de lignes : ne pas
   mettre en cache une réponse issue du repli IMAP, et évincer `Mail.Email` à la persistance de
   l'enrichissement. Test d'abord, commit `fix(mail)` séparé. Il faut alors **retirer AUD-27 de
   task-342** pour éviter un double traitement.
2. **(b) Mettre `E2E-BIO-001` en quarantaine** jusqu'à task-342, avec l'étiquette citant la task
   de correction. C'est la seule échappatoire prévue par la task-347, et **seul l'humain la pose**.
   Le run devient vert. Le DOD de 345 (« run vert deux fois de suite ») est alors tenu avec un
   scénario en quarantaine déclarée.
3. **(c) Livrer 345 rouge**, en l'état : la PR montre le filet qui détecte un défaut réel.
   `/review` refuserait de toute façon d'ouvrir la PR sur un DOD non tenu.

**Recommandation : (a).** Le filet vient de prouver que ce défaut touche un parcours clinique :
l'acquittement de biologie. Le correctif est local, et le mettre en quarantaine reviendrait à
couper le filet précisément là où il vient de mordre.

## Ce qui est déjà fait (et reste valable quel que soit le choix)

- **api-mail** `feat/task-345-filet-e2e-headless-mobile` : `1d5d9e45` (backend e2e, seed,
  relais, catalogue, parité) et `61e18424` (fix : compteur de pièces jointes sur le chemin des
  en-têtes IMAP).
- **client-mobile** : `3004950` (filet headless) et `bca017d` (fix : le menu des dossiers se ferme
  après le choix d'un dossier).
- **Suites des repos vertes** : api-mail 5 735 tests (0 échec, 16 ignorés préexistants), mobile
  943/943 ; builds 0 erreur.
- Rien n'est poussé. La passe qualité `/simplify` (§Q) et le push se feront à la reprise.

## Autres constats du filet, hors périmètre, à router vers le PO

- **Dates des messages** : `EmailBuildingService.MapHeaderFields` pose
  `SentDate = envelope.Date?.LocalDateTime` (horloge de l'hôte). Un message servi par le chemin
  IMAP et le même relu en base n'ont pas la même heure : un message reçu ou déplacé change de rang
  dans la liste (jusqu'à 2 h d'écart constatées). C'est la famille d'**AUD-28** (task-342, lot C).
- **« Aucun contenu disponible »** s'affiche pendant le chargement du détail d'un mail, avant
  l'arrivée du corps. C'est trompeur pour le praticien. Petite US mobile possible.
