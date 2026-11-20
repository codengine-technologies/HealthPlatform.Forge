# task-462 — revue anticipée arrêtée au passage 3 (règle 13), arbitrage requis

**Étape** : `/review task-462 --code`, passage 3 (après 2 reprises sur 5).
**État** : task en `wip-*`. Branches poussées : api-mail `dc39d1d3`, client-mobile `82fc95e`, dtos-mss `d668837`
(630.0.0 publié) ; client-angular non commité (code-only). Le détail est dans le task file (`## Develop log`,
`## Code Review Summary`, passages 1 à 3).

## Pourquoi la chaîne s'arrête

1. **Règle 13 (troisième apparition d'un même bloquant)** — deux familles de bloquants reviennent pour la troisième fois,
   avec une cause nouvelle à chaque fois :
   - **B1 → F2/F3 → R1** : le retour d'un rappel dépend du « plancher » de la Boîte de réception (les messages arrivés
     depuis la demande doivent être en base). Passage 3 : sur un succès de cache de `GetFolderAsync`, l'`UIDVALIDITY` vaut
     0, le plancher disparaît et toute la Boîte de réception est attendue (le rappel peut ne jamais revenir tant que
     l'historique n'est pas ingéré). Les tests d'intégration simulent le cache et ne le voient pas.
   - **B2 → F1 → R2** : un échec de remise doit clore le rappel. Passage 3 : un rebond arrivé **avant** le relevé du
     plancher (rappel posé depuis le détail après le rebond, ou rebond rapide entre l'envoi SMTP et le relevé) est sous le
     plancher, jamais lu, et le message non distribué revient « Sans réponse ».
   - **R3** (règle 1b) : la branche « le retour attend tant qu'il reste des accusés à lire » n'est prouvée que par un
     test unitaire.
2. **Une décision vous revient** : le correctif de R2 dépend de l'arbitrage AH1, resté ouvert depuis le passage 1.

## Ce qu'il faut trancher

**Q1 — AH1 : quelles réponses clôturent un rappel posé depuis le détail d'un message déjà envoyé ?**
- (a) **Recommandé** : seules les réponses (et les échecs de remise) arrivés **après la demande**. Le plancher est alors
  l'`UIDNEXT` relevé à la demande, comme aujourd'hui. Pour un rappel posé à l'envoi, le relevé se fait **avant** l'envoi
  SMTP (corrige le rebond rapide de R2). Une réponse antérieure à la demande ne clôt plus le rappel.
- (b) Toute réponse depuis l'envoi compte (comportement actuel pour la clôture). Le plancher doit alors être relevé **à
  l'envoi de tout message**, même sans rappel, pour qu'un rappel posé plus tard depuis le détail en hérite. Cela demande
  un relevé STATUS sur chaque envoi et une table ou une colonne de plus.

**Q2 — AH2 : une réponse automatique d'absence (`Auto-Submitted`) clôt-elle le rappel ?**
Recommandé : non (exclure `Mails.IsAutomatic`), et ne compter que les expéditeurs parmi les destinataires (À, Cc) de
l'envoi.

**Q3 — AH3 : un échec de remise partiel (un destinataire sur plusieurs) clôt-il le rappel ?**
Recommandé : non, seulement si tous les destinataires sont en échec.

**Q4 — reprise** : une fois Q1 tranchée, faut-il relancer la chaîne (`/develop task-462 --reprise`, 3 reprises restantes)
avec R1, R2, R3 et vos décisions ? Le correctif de R1 est sans décision : porter `UidValidity` dans `FolderStatusCache`
(ou relire un STATUS frais pour le plancher), avec un test d'intégration sur un vrai cache.

## Autres points en attente de vous

- Le plan de contrôle a des commits locaux non poussés, dont `480fcbd` (`Tools/contracts/contract_impact.py` cherche
  la surface sur develop **et** sur la branche) : c'est un changement de la chaîne, qui attend votre relecture avant le
  push (règle d'or 7).
