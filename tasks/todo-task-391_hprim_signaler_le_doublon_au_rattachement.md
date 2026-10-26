# todo-task-391.md — Rattacher un résultat HPRIM déjà présent dans le dossier du patient : signal doublon

**Repos**: api-mail
**Dependencies**: task-389 (le document HPRIM existe, dans la file « à intégrer »), task-390 (résultats structurés)
**Epic**: E009
**Single frontend**: true
**Priorité**: **3** — un laboratoire qui renvoie le même résultat (renvoi, double adressage) produit deux documents identiques. Une fois rattachés au même patient, ils restent côte à côte sans que rien ne le signale.

> **Origine.** Séance `/po` du 2026-10-23 (parsing HPRIM), suite de task-389 et task-390.
> **Périmètre réduit par l'humain le 2026-10-26** : cette US ne livre que le **signal doublon**.
> - Le remplacement d'un résultat partiel par le complété est **abandonné** : le partiel et le complété restent tous deux visibles, le partiel marqué « partiel » (task-390, task-392).
> - La suggestion de patient par traits existe déjà (task-012, task-137) et n'est pas modifiée.
>
> **US backend seule (justification)** : le bandeau doublon et la décision du médecin existent déjà dans le mobile et weda2 (task-013). Ils s'affichent pour un document HPRIM sans changement côté client. Le signal est prouvé par test d'intégration ; aucun parcours médecin nouveau, donc pas de scénario e2e (arbitrage du 2026-10-26).

## Ce qui est établi

- **Rattachement existant** (task-012, task-137, task-331) : `POST medical-documents/{id}/attach-patient`. Le médecin choisit une fiche existante, jamais créée depuis le rattachement.
- **Signal doublon existant** (task-013) :
  - un document porte `DuplicateOfId` (`IsDuplicate` dans la réponse) ;
  - le client affiche un bandeau, et le médecin garde ou écarte (`POST medical-documents/{id}/duplicate-decision`) ;
  - un doublon non tranché reste visible : rien n'est masqué sans le médecin.
- **Aucune détection à la réception pour un document sans INS** (task-193, décision 6 de task-389) : un HPRIM n'a jamais d'INS, il n'est rapproché de rien à son arrivée. Le rapprochement se fait **au rattachement**, contre le seul dossier du patient choisi par le médecin.
- **Un fichier `.hpm` peut porter plusieurs résultats**, donc plusieurs patients (task-389 : un document par résultat). Un même résultat peut être renvoyé seul ou regroupé avec d'autres, et dans un autre encodage.

## Décisions actées (humain, 2026-10-26)

1. **Périmètre** : seul le signal doublon. Ni remplacement du partiel, ni changement de la suggestion de patient.
2. **Reconnaissance du « même résultat »** : par une **empreinte de son contenu**, proposée par l'humain et précisée en séance.
   - Une empreinte **par résultat**, pas par fichier : en-tête et texte du résultat.
   - Calculée sur le contenu **décodé**, aux fins de ligne normalisées : le même résultat renvoyé dans un autre encodage ou regroupé autrement garde la même empreinte.
   - Algorithme **SHA-256** (MD5 est signalé comme faible par l'outillage qualité, sans gain ici).
   - Elle est conservée avec le document. Le n° de dossier du laboratoire n'est pas conservé.
3. **Backend seul**, sans scénario e2e.

## Objective

Quand le médecin rattache un résultat HPRIM à un patient dont le dossier contient déjà le même résultat, le document rattaché porte le signal doublon existant. Le médecin garde ou écarte, comme pour un CDA.

### Règles métier

- **Même résultat** = même empreinte de contenu (décision 2).
- **Au rattachement seulement**, et **seulement contre le dossier du patient choisi**. Il porte sur les documents HPRIM déjà rattachés à ce patient. Un document d'un autre patient, ou encore à intégrer, n'est jamais comparé ni touché.
- **Le document rattaché en second** porte le signal doublon et désigne le premier. Le premier est inchangé.
- **Rien n'est masqué automatiquement** : le doublon reste visible jusqu'à la décision du médecin, avec le bandeau et les choix existants (task-013).
- **Résultats différents** (une valeur, une ligne ou un statut change, par exemple le partiel et son complété) : empreintes différentes, aucun signal. Les deux restent visibles.
- **Détacher** le premier document laisse le second visible ; le signal suit les règles existantes de task-013.
- **Documents HPRIM reçus avant cette US** (sans empreinte) : ils ne sont rapprochés de rien.
- **BAL déléguée** (règle 14) : un document délégué n'est jamais rattachable (task-398). Aucune empreinte n'est conservée chez le délégataire, rien n'est persisté.

## Definition of Done

- [ ] Build et tests verts : api-mail
- [ ] Empreinte SHA-256 du contenu décodé du résultat (en-tête et texte, fins de ligne normalisées), conservée avec le document HPRIM. Migration de la base mail : colonne nullable, sans effet sur les documents existants
- [ ] ≥ 1 test unitaire par règle d'empreinte :
  - même résultat → même empreinte, y compris dans un autre encodage, avec d'autres fins de ligne, ou regroupé dans un fichier à plusieurs résultats ;
  - une valeur ou un statut différent → empreinte différente ;
  - deux résultats d'un même fichier → deux empreintes
- [ ] Test d'intégration de bout en bout (règle 1b) pour `POST attach-patient` :
  - **nominal** : le même HPRIM est reçu deux fois, et les deux documents sont rattachés au même patient. Le second porte le signal doublon (`IsDuplicate`, `DuplicateOfId` = le premier), lu dans la réponse réelle du contenu du message et des documents du patient. Le premier n'en porte pas, et aucun n'est masqué ;
  - **cas d'échec** : un HPRIM dont une valeur diffère n'est pas signalé ;
  - **autre patient** : le même résultat rattaché à deux patients différents n'est pas signalé ;
  - vu rouge
- [ ] Test d'intégration : la décision du médecin sur le doublon HPRIM (`duplicate-decision`) suit le comportement existant de task-013
- [ ] **BAL déléguée — test d'intégration** (banc de délégation de task-397) : un HPRIM délégué n'expose aucun identifiant rattachable, et la base du délégataire ne contient aucun document ni empreinte pour ce message ; vu rouge (règle 1b)
- [ ] Aucune donnée de santé en clair dans les journaux : ni trait patient, ni valeur, ni empreinte

## Manual Test Plan

Lancer l'AppHost, puis le mobile (`cd Client/Mobile && npm start`) et weda2. Se connecter en Cyril par PSC.
Messages de test : le même HPRIM synthétique déposé **deux fois** dans la Réception de Cyril (`.eml` comme pour task-389), puis une variante dont une valeur diffère.

1. Rattacher le premier document à une fiche existante : aucun bandeau.
2. Rattacher le second à la **même** fiche : le bandeau doublon s'affiche ; « garder » et « écarter » fonctionnent comme pour un CDA.
3. Rattacher la variante (valeur différente) à la même fiche : aucun bandeau.
4. Rattacher le même résultat à une **autre** fiche : aucun bandeau.
5. Seq : aucun trait patient, aucune valeur, aucune empreinte.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : biologie médicale (réception en médecine de ville)
- **Vague Ségur** : hors Ségur — HPRIM, format historique hors CI-SIS
- **Exigences DSR honorées** : identito-vigilance — aucun rapprochement avant le choix explicite du patient par le médecin ; rapprochement limité au dossier de ce patient ; rien n'est masqué sans décision du médecin
- **INS** : non applicable — le HPRIM ne porte pas d'INS ; l'empreinte ne sert jamais à identifier un patient
- **Authentification PS** : inchangée — PSC / e-CPS de la session de messagerie
- **Habilitations** : documents de la boîte du médecin. BAL déléguée : aucun rattachement possible (règle 14, task-398)
- **Interop CI-SIS** : non applicable — HPRIM Santé
- **Tracé PGSSI-S** : rattachement déjà tracé (task-012) ; la décision sur un doublon suit le tracé existant (task-013) ; aucun nouvel évènement
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangée — l'empreinte est dérivée d'un compte rendu déjà reçu et conservé avec lui ; elle n'est ni exposée ni journalisée
