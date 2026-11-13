# todo-task-484 — Forge : suivre le contrat lu par les clients mobile et Angular

**Repos**: forge *(plan de contrôle `HealthPlatform.Forge` : racine du workspace, hors table des repos de code)*
**Dependencies**: le commit du plan de contrôle « la forge suit le contrat qu'api-mcp consomme » (2026-11-13,
`Tools/contracts/mcp_impact.py`), à pousser avant cette task
**Single frontend**: true
**Priorité**: 2. Elle comble le trou que `/e2e` laisse ouvert : un champ qu'aucun parcours n'affirme.

> **Mode d'exécution.** Le plan de contrôle n'est pas un repo de code de la table : `/start` n'y crée pas de branche
> et `/develop` ne le prend pas en charge. Cette task est implémentée **dans une session Claude, à la demande de
> l'humain**, qui **relit le diff avant le push** sur `develop` (règle 5 : le plan de contrôle se pousse sans PR). Elle
> modifie la chaîne elle-même, d'où cette relecture explicite (règle d'or 7).

> **Origine.** Demande humaine du 2026-11-13, après l'intégration d'api-mcp : « est-ce que ce mécanisme existe pour
> client-angular et client-mobile ? ». Non : il n'existe que pour api-mcp.

## Ce qui est établi

- client-mobile et client-angular recopient **à la main** les contrats d'api-mail dans leurs propres modèles
  TypeScript (CLAUDE.md, « Cross-repo dependencies »). Un changement de dtos-mss ou d'api-mail ne les fait jamais
  échouer à la compilation.
  - client-mobile : 23 fichiers de modèles (`Client/Mobile/src/app/core/models/`). Les interfaces portent le nom des
    classes C# (`FolderDto`, `MailAddressDto`, `ContactDto`, `DraftDto`…). 18 fichiers appellent des routes
    `api/v1/…`.
  - client-angular : 29 fichiers de modèles (`Client/Angular/front/libs/mss/src/core/models/`), et 18 fichiers qui
    appellent des routes.
- Le filet actuel est **`/e2e`**, bloquant : quand une task touche api-mail ou dtos-mss, les deux voies rejouent les
  parcours du médecin contre le vrai backend. Il ne voit pas **un champ qu'aucun scénario n'affirme** : l'écran
  affiche alors un vide, sans rouge. Et quand il bloque, rien n'ajoute le client à la task ni n'adapte ses modèles.
- Seul garde-fou ciblé existant : la règle `AuditActionType` de `agents/develop.md` (report dans le modèle Angular).
- `Tools/contracts/mcp_impact.py` fait déjà ce travail pour api-mcp. Ses comparateurs côté api-mail et dtos-mss
  (champs, types, routes, énumérations par rang, codes d'erreur, forme du JSON) sont réutilisables.
  - La surface consommée y est déduite du code du consommateur.
  - Une surface introuvable sur `origin/develop` donne une erreur, jamais un feu vert silencieux.
  - Un consommateur touché est ajouté à la task par une branche paresseuse.

## Objective

Quand une task modifie dans api-mail ou dtos-mss un élément qu'un client lit, la forge le détecte **avant `/e2e`**,
ajoute ce client à la task et adapte ses modèles. Le médecin ne découvre plus un champ vide après le merge.

## Règles métier (de la forge)

1. **La surface d'un client se déduit de son code**, comme pour api-mcp, jamais d'une liste tenue à la main :
   - les interfaces et types de ses dossiers de modèles qui portent le **nom d'une classe de dtos-mss** (mobile : même
     nom ; Angular : même nom, ou table de correspondance déclarée dans l'outil). Leurs champs sont lus en
     minuscules ; un champ optionnel (`?`) compte comme lu ;
   - les routes `api/v1/…` que ses services appellent, gabarits normalisés (`{}` pour un segment variable).

   Une interface sans classe correspondante est un **modèle de vue local** : elle n'entre pas dans la surface, et
   `surface` la liste à part.
2. **Mêmes impacts qu'api-mcp** : champ lu qui disparaît ou change de type, route appelée qui disparaît, énumération
   modifiée, code d'erreur retiré, forme du JSON modifiée. Ajouter un champ n'est jamais un impact.
3. **client-mobile touché** : branche paresseuse créée par `/develop` (comme dtos-mss et api-mcp), `client-mobile`
   ajouté aux `**Repos**`, modèles et services adaptés, tests unitaires du client et scénario e2e concerné mis à jour.
4. **client-angular touché** (mode code seul) : `/develop` adapte les fichiers sur la branche déjà extraite par
   l'humain, **sans aucune opération git**. La liste des fichiers modifiés et la raison de chaque changement vont dans
   le `## Develop log`, puis dans le rapport final, pour l'humain qui commite et pousse sur TFS.
5. **Jamais de feu vert silencieux** : une classe, une route ou un modèle client introuvable donne une erreur d'outil
   (code 2), comme pour api-mcp. Un champ isolé absent reste un avertissement.
6. **`/e2e` ne change pas** : il reste le filet à l'exécution, joué après. Cet outil agit avant, sur le code.

## Comportement attendu

- `python Tools/contracts/mcp_impact.py check` (ou un outil renommé, par exemple `contract_impact.py`, avec
  `mcp_impact.py` gardé comme alias) rend un verdict **par consommateur** :
  ```
  api-mcp        : aucun impact
  client-mobile  : IMPACT — MailDto.subject disparaît (lu par core/models/mail.model.ts)
  client-angular : aucun impact
  ```
  Code de sortie : 0 si aucun consommateur n'est touché, 1 si au moins un l'est, 2 sur une erreur d'outil.
- `surface --consumer client-mobile|client-angular|api-mcp` affiche la surface de ce consommateur, et ses modèles de
  vue locaux à part.
- Playbooks :
  - `/po` liste les clients touchés dans les `**Repos**` ;
  - `/develop` étend son Step 4c aux deux clients (règles 3 et 4) ;
  - `/review` étend son étape 4c : un impact non traité donne un CHANGES REQUESTED corrigeable ; pour client-angular,
    l'impact traité est vérifié sur l'arbre de travail non commité ;
  - CLAUDE.md décrit le mécanisme pour les trois consommateurs.

## Definition of Done

- [ ] L'outil déduit la surface des deux clients de leurs vrais fichiers. Un test affirme au moins `FolderDto`,
      `MailAddressDto` et la route `GET api/v1/account/mailboxes` pour client-mobile, et une interface de
      client-angular rattachée à sa classe C#.
- [ ] Tests sur dépôts temporaires alimentés par les vrais fichiers (même méthode que `test_mcp_impact.py`) :
  - champ lu par le mobile retiré → impact client-mobile ;
  - champ lu par l'Angular retiré → impact client-angular ;
  - route appelée par un client retirée → impact ;
  - champ ajouté → aucun impact ;
  - modèle de vue local → hors surface ;
  - modèle client rattaché à une classe introuvable sur `origin/develop` → code 2.
- [ ] Tests vus rouges par mutation : comparaison neutralisée, puis rattachement par nom neutralisé.
- [ ] Les 13 tests existants de `test_mcp_impact.py` restent verts (aucune régression pour api-mcp).
- [ ] `agents/po.md`, `agents/develop.md` (Step 4c), `.claude/commands/review.md` (étape 4c) et `CLAUDE.md` mis à
      jour.
- [ ] Le `## Develop log` cite, sur la branche de task-466 si elle est encore ouverte, le verdict de l'outil pour les
      trois consommateurs.

## Manual Test Plan

1. `python -m unittest Tools/contracts/test_mcp_impact.py` : tous les tests sont verts.
2. `python Tools/contracts/mcp_impact.py surface --consumer client-mobile`. Vérifier que `MailDto`, `FolderDto`,
   `MailboxDto` et leurs champs apparaissent, et que les modèles de vue locaux sont listés à part.
3. Même commande pour `client-angular`.
4. Sur une branche jetable de dtos-mss, renommer un champ lu par le mobile (par exemple `Subject` de `MailDto`), puis
   `check` : verdict « IMPACT » pour client-mobile **et** api-mcp, qui citent le champ. Annuler le changement.
5. Lire les playbooks modifiés : une task qui touche ce que lit le mobile fait entrer `client-mobile` à `/develop`,
   et une task qui touche ce que lit l'Angular produit la liste des fichiers à commiter sur TFS.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — outillage de la chaîne de développement
- **Vague Ségur** : hors Ségur — même raison
- **Exigences DSR honorées** : non applicable — aucune fonction du produit n'est modifiée
- **INS** : non applicable — l'outil lit du code, aucune donnée patient
- **Authentification PS** : non applicable — aucun parcours d'authentification modifié
- **Habilitations** : non applicable
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : non applicable — aucun acte sur une boîte
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : non — l'outil tourne sur le poste de développement, sur du code source
- **AIPD / impact RGPD** : inchangé — aucun traitement de données personnelles

## Notes techniques (orientations, non contractuelles)

- Analyser le TypeScript par expressions régulières, comme le C# dans `mcp_impact.py` :
  - `export interface X { champ?: type; }` et `export type X = { … }` ;
  - les URL des services en littéraux ou en gabarits (`` `${API}/api/v1/account/mailboxes` ``) ;
  - pas d'analyseur TypeScript complet : le garde-fou « surface introuvable » couvre ses limites.
- Côté Angular, vérifier si les interfaces portent le nom C# ou un nom métier (`Mail`, `Folder`). Dans le second
  cas, une table de correspondance déclarée dans l'outil, comme `RECORD_TO_DTO` pour api-mcp.
- Les comparateurs côté api-mail et dtos-mss existent déjà ; seule la surface change par consommateur. Factoriser
  par une classe `Consumer` (nom, surface, dépôt, mode git : pushable ou code seul).
