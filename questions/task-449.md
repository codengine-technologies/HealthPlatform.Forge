# task-449 — /review passage 6 : CHANGES REQUESTED, après la reprise 5

**Étape** : `/review` (validation finale), 6ᵉ passe, 2026-11-12. Sonar (CA1862 corrigé, aucun avertissement au
build) et `/e2e` (mobile 61, angular 84, parité verte) sont verts. B1, B2, S5 de la passe 5 tiennent. La PR n'est
**pas** ouverte. La task reste en `wip-*` (`**Reprises**: 5`).

## Bloquant (passe 6) — corrigeable par la forge, une ligne

### B1 — Un correspondant choisi dont l'adresse est longue est refusé en 400

- Le plafond de 10 mots (S5) compte les mots d'une adresse alors qu'elle est comparée en entier (B2). Choisir
  `secretariat.cardiologie.pediatrique@ch-saint-jean-de-luz.mssante.fr` répond 400 « au plus 10 mots ». Vérifié
  dans le code.
- Correctif : le plafond ne s'applique qu'à un critère lu en mots. Test d'intégration avec une adresse longue, vu rouge.

## Suggestions (même reprise)

- **S1** — `de : ""` (paire vide seule) n'est plus refusé comme critère vide ; `de : "Paul Martin" ""` lance une
  recherche par le sens sur `""`. Un critère ou un reste fait de blancs et de paires vides est vide.
- **S2** — le serveur reconnaît comme adresse `p.martin@x.fr,` (virgule collée) que weda2 refuse : reprendre la même
  classe de caractères que le front.
- **S3** — le plafond compte les doublons et les élisions (`l'IRM` = 2 mots) : compter les mots distincts.

## Arbitrage humain

Aucun.

## Pourquoi la chaîne s'arrête

Cinq reprises faites (plafond 2 ; les reprises 3 à 5 demandées par l'humain). Le bloquant est né du correctif S5 de la
reprise 5, comme les précédents sont nés du correctif d'avant ; la prévention est consignée (`conventions/csharp.md` :
une règle de critère se teste pour ses deux lectures, adresse et mots). Correctif d'une ligne : la forge recommande une
6ᵉ reprise (`relance`).
