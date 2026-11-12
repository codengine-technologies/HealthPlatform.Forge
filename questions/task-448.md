# task-448 — /review : arbitrage S1 / S4 ouvert (bloquants résolus)

> **Mise à jour 2026-11-12 (passage 2)** : B1, B2, S5, S6, S8 **résolus** par la reprise de `/develop`, prouvés rouges
> (`## Develop log` § Reprise). `/review` : **APPROVED**, PRs ouvertes (api-mail #363, dtos-mss #62, label
> `awaiting-human-merge`), task en `done-*`. **Restent ouverts, à trancher au HAG : S1 et S4** (section « Arbitrage
> humain »). Une décision qui change le comportement repasse par `/develop task-448` avant le merge.

**Étape** : `/review` (revue indépendante, 2026-11-12). Build et tests verts (api-mail, weda2), Sonar QG OK, `/e2e` vert.
Passage 1 : la PR n'était pas ouverte, la task restait en `wip-*`.

## Bloquants

### B1 — « Marquer non lu » ne laisse aucune trace (règle 14, DoD « une trace par message et par action »)

- `BulkMailActionService` passe par `IEmailFlagService.UpdateEmailUnReadStatusAsync`
  (`src/Application/Services/Implementation/EmailFlagService.cs:118`). Ce geste écrit en base et enfile la
  propagation, mais n'appelle **jamais** `auditService.Trace`. « Marquer lu » trace `MailRead`, « étoile » et « sans
  étoile » tracent `MailFlagChange` ; seul « non lu » ne trace rien.
- Défaut **antérieur** du geste unitaire, que l'action groupée multiplie : un délégataire remet 2 000 résultats en non
  lu, et le journal n'en dit rien.
- Correctif attendu : une trace `MailFlagChange` par message dans `UpdateEmailUnReadStatusAsync` (comme
  `TraceFlagChange`), prouvée par un test d'intégration qui la lit dans le journal de la boîte, au nom de la personne.

### B2 — Corbeille et refus « Corbeille depuis la Corbeille » non prouvés sur la vraie pile (règle 1b)

- La mise à la Corbeille et le refus depuis la Corbeille (la garde contre la suppression définitive) ne sont prouvés
  que par des tests unitaires qui simulent le type de dossier. Rien ne prouve sur la vraie pile que la liste des
  dossiers a enregistré `FolderType.Trash` pour la Corbeille de Dovecot. C'est pourtant ce type que lit la garde, et
  `ImapService.DeleteEmailsAsync` choisit l'effacement définitif selon `ImapHelper.GetFolderType`.
- Non prouvés de bout en bout non plus : étoile, sans étoile, non lu, et des résultats répartis sur plusieurs dossiers.
- Tests attendus, chacun vu rouge par mutation :
  - INBOX → Corbeille : les messages sont dans la Corbeille, chaque mise à la Corbeille est au journal ;
  - Corbeille → Corbeille : `already_in_trash`, et les messages sont **toujours sur le serveur** (mutation de la
    garde) ;
  - étoile, sans étoile et non lu : l'état en base et une trace par message ;
  - des résultats de deux dossiers.

## À corriger dans la même reprise (non bloquant seul, défaut réel)

- **S6** — La confirmation en attente n'est pas effacée quand la recherche change. Si le médecin relance une recherche
  pendant « Déplacer 342 messages vers Archives ? », la question reste affichée au-dessus des nouveaux résultats, et
  « Confirmer » agit sur l'ancien périmètre. Il faut effacer `pending` au changement de requête.
- **S5** — Une Corbeille refusée parce que la liste des dossiers n'a jamais enregistré le type du dossier rend la raison
  `failed`, que le client propose de réessayer : l'essai échoue pareil. Il faut une raison distincte, non proposée au
  nouvel essai.
- **S8** — Le commentaire de `ToKeys` parle encore d'« un résultat de plus que le plafond », supprimé par `/sonar`.

## Arbitrage humain (suggestions à trancher, hors reprise sauf décision)

- **S1** — Une remise en « lu » groupée trace `MailRead`, qui atteste l'**accès** au message (commentaire de
  `EmailFlagService`). 2 000 résultats marqués lus écrivent 2 000 attestations d'accès qui n'ont pas eu lieu.
  Question : faut-il un type d'acte propre (ou `MailFlagChange`) pour un marquage sans lecture ?
- **S4** — « Tous les résultats » inclut les résultats **proches par le sens** (partie « Similaires », seuil 0,45).
  Une mise à la Corbeille de 342 résultats peut donc toucher des messages qui ne contiennent pas les mots cherchés.
  Question : faut-il limiter l'action groupée aux résultats exacts (« Tous les mots » / « Une partie des mots »), ou
  dire dans la confirmation combien sont des résultats proches ?
- **S2 / S3** — Comptes rendus optimistes dans les cas limites : un déplacement vers le dossier même compte des succès
  sans rien faire, et un message déjà effacé est compté comme mis à la Corbeille. Si le médecin quitte la vue en cours
  d'action, les morceaux restants sont abandonnés sans compte rendu.
- **S7** — Coût : environ 4 allers-retours SQL par message pour les drapeaux (8 000 requêtes pour 2 000 messages,
  bornées par morceaux de 100). Acceptable en v1.

## Reprise

`/develop task-448` corrige B1, B2, S5, S6, S8, chaque correctif vu rouge, puis la chaîne reprend jusqu'à `/review`.
