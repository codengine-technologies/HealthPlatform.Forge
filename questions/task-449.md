**Résolu le 2026-11-12** — reprise 7 approuvée par la revue anticipée (passe 8), `/sonar` et `/e2e` verts sur le code approuvé, PR api-mail #367 et dtos-mss #65 ouvertes (`awaiting-human-merge`).

# task-449 — revue anticipée passe 7 : CHANGES REQUESTED, après la reprise 6

**Étape** : `/review --code` (revue anticipée, boucle courte), 7ᵉ passe, 2026-11-12. Les correctifs de la reprise 6
(B1, S1, S2, S3) tiennent là où ils visaient ; api-mail 8 003 tests verts. La PR n'est **pas** ouverte. La task reste
en `wip-*` (`**Reprises**: 6`).

## Bloquant (passe 7) — corrigeable par la forge

### B1 — Le nombre de conditions SQL d'un critère n'est plus borné

- Vérifié dans le code : entre guillemets, les mots ne sont pas dédoublonnés et les mots d'une lettre ne comptent pas au
  plafond. `objet : "a a a … a"` produit ~245 conditions identiques par ligne de la boîte. Et l'exemption « adresse »
  du plafond vaut aussi pour « Objet », qui ne compare pas l'adresse en entier.
- Correctif : **une borne dure unique** sur les conditions réellement émises (mots distincts), posée là où le SQL est
  construit ; l'exemption « adresse » seulement pour « De » et « À ». Tests rouges sur les deux cas.

## Suggestions (même reprise)

- **S1** — `""` seul dans un champ du formulaire liste toute la boîte (la barre répond 400) : aligner.
- **S2** — dédoublonner sans passer par le jumeau C# de la normalisation.
- **S3** — le test « l'IRM … » doit lire le message trouvé, pas seulement le code 200.

## Arbitrage humain

Aucun.

## Pourquoi la chaîne s'arrête

Six reprises faites (plafond 2). C'est le 3ᵉ correctif successif du plafond de mots qui ouvre un trou ; la prévention
retenue (`conventions/csharp.md`) est de poser **une seule** borne, sur ce qui est émis, au lieu d'exemptions. Cette
passe a coûté ~3 min (boucle courte, sans Sonar ni e2e) au lieu de ~45. La forge recommande une 7ᵉ reprise (`relance`).
