# todo-task-192.md — Recherche : résultats silencieusement écartés (déduplication sur l'UID) et casse non ignorée

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe métier MSSanté).

> ### Re-vérification du 2026-08-23 — **toujours pertinente, et le défaut de casse est plus large qu'écrit**
>
> Chaque preuve rejouée sur `develop`. Les numéros de ligne du bloc « Preuve »
> datent du 2026-07-25 ; **la colonne « au 2026-08-23 » fait foi**.
>
> | Preuve | 2026-07-25 | Au 2026-08-23 | État |
> |---|---|---|---|
> | Déduplication sur l'UID | `SemanticSearchRepository.cs:513-515` | **`:579`** — `.GroupBy(x => x.Uid).Select(g => g.First())` | inchangé |
> | Fenêtre ordonnée sur l'UID | — | **`:572`** — `OrderByDescending(x => x.Uid)` puis `Take`, par terme | inchangé |
> | Casse hétérogène | `:597-632` — « patients en `ILike`, sujet/expéditeur en `Like` » | **inversé, et pire** : le **seul** `ILike` porte sur le corps (**`:571`**) ; sont en `Like` **sensible à la casse** : nom/prénom **patient** (`:98-99`, `:186-187`, `:260-261`, `:319-320`), `FromAddress`/`FromName` (`:674-675`, `:680`) et `Subject` (`:685`) | **plus large** |
> | Jokers non échappés | — | **confirmé : 0 échappement** dans le fichier — aucun `Escape`, aucun remplacement de `%`/`_` | inchangé |
>
> **Correction d'une erreur de la preuve d'origine, qui change le périmètre** :
> la recherche par **nom de patient** n'est **pas** insensible à la casse, contrairement
> à ce qu'affirmait la preuve du 2026-07-25. Chercher « DUPONT » ne trouve pas
> « Dupont ». C'est le champ le plus utilisé cliniquement, et c'est donc lui qui
> justifie le point 3 en priorité — pas le sujet.
>
> **Dépendance levée** : la task s'appuyait sur « l'identité de mail assainie par
> task-179 ». task-179 est **mergée** (`tasks/archived/`) — le point 1 peut donc
> être livré sur cette identité, sans attente.

## Objective

Rendre la recherche **exhaustive**. Une recherche multi-dossiers écarte aujourd'hui
des résultats pertinents sans le signaler, parce qu'elle déduplique les candidats
sur le seul **UID IMAP** — un identifiant qui n'est unique qu'au sein d'un dossier
(et pour une UIDVALIDITY donnée). Chaque dossier ayant sa propre numérotation
démarrant à 1, les collisions sont la règle, pas l'exception.

S'y ajoute une incohérence de casse : les filtres sur le sujet et l'expéditeur sont
**sensibles à la casse**, alors que ceux sur les noms de patients ne le sont pas.
Chercher l'expéditeur « dupont » ne trouve pas « DUPONT ».

Pour un praticien, une recherche qui cache un résultat sans le dire est plus
dangereuse qu'une recherche qui échoue franchement.

**US backend-only (justification)** : requêtes de recherche côté serveur.

### Preuve (état actuel du code)

- `src/Infrastructure/Repository/SemanticSearchRepository.cs:513-515` — la
  déduplication écrase les homonymes d'UID :
  `allCandidates.GroupBy(x => x.Uid).Select(g => g.First())`.
  Les trois appelants (`:397-435`) autorisent explicitement une recherche sans
  dossier (`folderPath == null || m.FolderPath == folderPath`) — donc à l'échelle de
  toute la boîte.
- La fenêtre de candidats est `OrderByDescending(x => x.Uid).Take(n)` par terme :
  elle mélange les UID de dossiers différents **comme s'il s'agissait d'un ordre
  chronologique**, ce qui n'a aucun sens entre dossiers.
- `src/Infrastructure/Repository/SemanticSearchRepository.cs:597-632` — les filtres
  Sujet / Nom d'expéditeur / Adresse utilisent `EF.Functions.Like`
  (**sensible** à la casse sous PostgreSQL) tandis que les noms de patients
  utilisent `ILike`. Par ailleurs les caractères `%` et `_` saisis par
  l'utilisateur ne sont **pas** échappés, dans les deux cas.

Lien avec task-179 : l'UID n'est unique que pour une UIDVALIDITY donnée. La
correction doit s'appuyer sur l'identité de mail assainie par task-179 plutôt que
de réintroduire une clé fragile.

### Contenu attendu

1. **Déduplication sur une identité réellement unique** — l'identifiant technique du
   mail, jamais l'UID seul. S'aligner sur l'identité définie par task-179.
2. **Ordonnancement cohérent** : la fenêtre de candidats doit s'ordonner sur une
   grandeur qui a un sens transverse aux dossiers (la date du message), pas sur
   l'UID.
3. **Casse homogène** : recherche insensible à la casse sur tous les champs
   textuels, y compris sujet, nom et adresse d'expéditeur.
4. **Échappement des jokers** : `%` et `_` saisis par l'utilisateur doivent être
   traités comme des caractères littéraux.
5. **Pas de perte muette** : si la recherche tronque volontairement (fenêtre de
   candidats, plafond de résultats), cela doit être **explicite** dans la réponse,
   afin que l'interface puisse indiquer au praticien que des résultats
   supplémentaires existent.

### Hors scope

- La pertinence sémantique et le rappel du moteur vectoriel (sujet distinct).
- L'identité des mails elle-même → task-179.
- Le contenu des logs de recherche → task-184.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire : deux messages de **dossiers différents** portant le **même**
      UID et correspondant tous deux à la recherche ⇒ **les deux** sont retournés
      (ce test doit échouer sur le code actuel — le vérifier explicitement)
- [ ] Test unitaire : la fenêtre de candidats s'ordonne sur la date du message, et
      un message récent d'un dossier archivé n'est pas écarté par un UID plus faible
- [ ] Test unitaire : recherche « dupont » trouve « DUPONT » et « Dupont » sur le
      sujet, le nom et l'adresse d'expéditeur
- [ ] Test unitaire : une saisie contenant `%` ou `_` est traitée littéralement
- [ ] Test unitaire : quand un plafond de résultats s'applique, la réponse le signale
      explicitement
- [ ] Non-régression : les recherches mono-dossier existantes retournent les mêmes
      résultats qu'avant (à l'exhaustivité près)
- [ ] Aucune requête de recherche brute journalisée (cohérence avec task-184)

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. **Collision d'UID** : dans la boîte de test, s'assurer d'avoir deux messages
   pertinents pour un même terme (« créatinine ») dans **deux dossiers différents**
   qui portent le même UID (par exemple `INBOX` UID 57 et `INBOX/Archives 2025`
   UID 57 — vérifiable dans les logs de synchronisation). Données anonymisées.
3. Lancer la recherche « créatinine » **sans filtre de dossier**. **Attendu** : les
   deux messages apparaissent. Avant correctif, un seul apparaît et l'autre est
   invisible, sans aucune indication.
4. **Casse** : rechercher l'expéditeur en minuscules alors que l'adresse est en
   majuscules → le message est trouvé. Avant correctif : aucun résultat.
5. **Jokers** : rechercher un terme contenant `%` → traité littéralement, pas comme
   un joker.
6. **Troncature** : lancer une recherche très large (terme fréquent) → si des
   résultats sont écartés par plafonnement, l'interface l'indique.
7. Non-régression : une recherche filtrée sur un seul dossier donne les mêmes
   résultats qu'avant le correctif.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volet MSSanté
- **Exigences DSR honorées** : correctif de conformité — accès effectif du praticien
  à l'intégralité des documents reçus
- **INS** : non applicable — la recherche par traits patients n'est pas modifiée
- **Authentification PS** : inchangée
- **Habilitations** : inchangées — la recherche reste circonscrite à la base du
  praticien
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : la recherche reste journalisée sans la requête brute
  (task-184) ; ne pas introduire de nouvelle journalisation de contenu ici
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé — pas de nouveau traitement. Risque
  d'exactitude/complétude (art. 5.1.d) à signaler : un praticien a pu conclure à
  l'absence d'un document qui existait.
