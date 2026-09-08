# questions/task-183.md — arbitrages d'identito-vigilance (INS NIA, OID de test, dossiers déjà scindés)

**Task** : `tasks/wip-task-183.md` — « `X-MSS-INS: O` annoncé pour une INS non
qualifiée (NIA, OID de test) ; l'OID est perdu à la persistance »
**Epic** : E009
**Ouvert le** : 2026-09-08 par `/develop`
**Statut** : en attente d'arbitrage humain (point 4 du task file)

> **Ce fichier n'est pas un blocage de la task.** Les points 1 et 2 sont livrés
> et testés sur la branche `fix/task-183-ins-oid-qualification` ; ils ne
> dépendent d'aucune des réponses ci-dessous. Seul le **point 3** (refus des OID
> de test en production) est en attente — voir « Ce qui reste à livrer ».

---

## Ce qui est déjà livré (et n'attend rien)

1. **L'annonce ne ment plus.** `X-MSS-INS: O` n'est émis que pour un OID du
   domaine NIR (`1.2.250.1.213.1.4.8`), traits d'identité exigés en complément.
   NIA, OID de test et OID inconnu donnent `N`. Le refus est journalisé par
   **classification** du domaine, sans matricule (tracé PGSSI-S).
2. **L'OID est persisté** (`MailPatients.Oid`, `MailMedicalDocuments.PatientOid`)
   et entre dans la clé d'identité patient : un matricule n'est plus interprété
   hors de son domaine, sur les deux chemins d'ingestion.

Effet de bord **déjà acquis** et qui répond partiellement à la question 3 : à
partir de maintenant, un document NIA et un document NIR de même matricule
n'atterrissent plus dans le même dossier, et un matricule de test ne fusionne
plus avec son homonyme de production. **La scission passée n'est pas réparée
pour autant** — c'est l'objet de la question 3.

---

## Question 1 — que doit-il advenir d'un document porteur d'une INS **NIA** ?

Le NIA est une identité **provisoire** (patient né à l'étranger, identité en
cours de qualification). Il désigne une personne réelle, mais son matricule peut
changer quand l'INS qualifiée est obtenue.

Deux options, cohérentes avec des règles déjà posées ailleurs :

- **(a) Rattachement au dossier, avec mention du statut** — le document rejoint
  un dossier patient clé sur le domaine NIA. Le praticien voit les documents,
  avec un marqueur « identité provisoire ». Coût : deux dossiers coexistent pour
  la même personne jusqu'à la qualification, et leur réunion est un acte manuel
  (question 3).
- **(b) Reprise manuelle, comme l'absence d'INS** (règle task-176) — aucun
  rattachement automatique ; le document reste dans la file d'intégration et le
  praticien le rattache lui-même. Coût : charge de travail sur des documents qui
  portent pourtant un identifiant exploitable.

**Ce que le code fait aujourd'hui** : (a) sans marqueur — le dossier est créé,
clé sur le domaine NIA, et rien dans l'interface ne dit que l'identité est
provisoire. C'est le prolongement du comportement existant, pas une décision.
Si (a) est retenue, il faut décider **où** le statut apparaît (liste de
documents ? en-tête du dossier ? les deux ?) — c'est une US produit distincte.

---

## Question 2 — que doit-il advenir d'un **OID de test** en production ?

Les OID `1.2.250.1.213.1.4.10` et `.11` sont réservés aux jeux d'essai. En
production, un document qui en porte un est **soit** un test échappé d'un
environnement de recette, **soit** une erreur d'émetteur. Dans les deux cas ce
n'est pas l'identité d'un patient réel.

Trois options :

- **(a) Rejet** — le document n'est pas ingéré, l'émetteur est notifié. Le plus
  net, mais un rejet perd un document que personne ne pourra plus retrouver si
  la classification était fausse.
- **(b) Quarantaine** — ingéré, marqué, invisible du dossier patient, visible
  d'un écran d'administration. Réversible.
- **(c) Ingestion marquée** — traité normalement, avec un marqueur visible. Le
  praticien décide.

**Ce que le code fait aujourd'hui** : (c) sans marqueur — le document est ingéré
et obtient son propre dossier (jamais fusionné avec la production, c'est déjà
acquis), mais rien ne le signale comme test. **C'est l'état de départ, pas la
cible.**

Sous-question qui vient avec : « en production » se détermine comment ? Un flag
d'environnement, un feature flag Flagsmith, ou une configuration par praticien ?
La réponse conditionne l'implémentation autant que le comportement retenu.

---

## Question 3 — faut-il **fusionner rétroactivement** les dossiers déjà scindés ?

Avant cette task, l'OID n'était pas stocké : les dossiers actuels sont clés sur
le matricule nu. Deux situations existent donc en base, et elles sont de nature
opposée :

- **Dossiers scindés** (même personne, deux dossiers) : ne se produisait
  **qu'entre** matricules **différents** (NIA et NIR d'une même personne ont des
  matricules distincts) — la scission est donc **antérieure et invisible** à la
  clé d'identité, avant comme après cette task. Les réunir demande d'apparier
  deux matricules **différents** comme désignant la même personne : c'est un acte
  d'identito-vigilance, pas une migration.
- **Dossiers fusionnés à tort** (deux personnes, un dossier) : possible quand un
  matricule de test coïncidait avec un matricule de production. Là, le dossier
  contient les documents cliniques de **deux personnes** — le cas le plus grave,
  et il faut savoir s'il s'est produit.

**Ce que la livraison fait aujourd'hui** : rien de rétroactif, délibérément. La
migration ajoute des colonnes nullables ; les lignes existantes portent
`Oid = NULL` (« domaine inconnu ») et **adoptent** le domaine du premier document
reçu qui en porte un, ce qui évite d'ouvrir un second dossier pour chaque
patient déjà connu. Aucune donnée de santé n'est réécrite.

Trois décisions demandées :

1. **Faut-il un inventaire** en lecture seule des dossiers susceptibles d'être
   concernés (matricules identiques sur des domaines différents, dossiers dont
   les documents portent des traits d'identité incohérents) ? C'est faisable et
   sans risque — c'est le préalable naturel, et le précédent existe (task-193 a
   livré un inventaire read-only plutôt qu'une remédiation).
2. **Selon quel protocole** une réunion ou une séparation de dossier
   s'effectue-t-elle ? Validation par le praticien ? Par le DPO ? Traçabilité
   attendue ?
3. **Qui porte l'acte** : la forge (US produit dédiée) ou une procédure
   d'exploitation ?

---

## Ce qui reste à livrer, et ce que ça attend

| Point du task file | État | Bloqué par |
|---|---|---|
| 1. Qualification par l'OID | **livré, testé** | — |
| 2. Persistance de l'OID + clé d'identité | **livré, testé** (migration auditée règle 7c) | — |
| 3. Refus des OID de test en production | **non livré** | question 2 (comportement **et** définition de « production ») |
| 4. Arbitrages | ce fichier | réponse humaine |

---

## AIPD / RGPD — à qualifier avec le humain (rappel du task file)

Un LPS destinataire a pu classer automatiquement, au titre d'une INS annoncée
qualifiée, un document qui ne l'était pas. Deux éléments à établir :

- **le volume** : combien de messages ont été émis avec `X-MSS-INS: O` sur un OID
  non-NIR ? Le tracé actuel ne permet pas de le reconstituer (l'OID n'était pas
  journalisé, et l'annonce non plus). Il n'est donc **pas mesurable
  rétroactivement** — seule une estimation par la part de documents NIA dans le
  corpus reçu est envisageable, et elle serait indicative ;
- **l'information des destinataires** : opportune ou non, et sous quelle forme.

C'est une question de conformité, pas de code — elle ne conditionne aucun des
points livrés.
