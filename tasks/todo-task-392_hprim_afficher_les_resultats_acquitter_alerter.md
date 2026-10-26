# todo-task-392.md — Résultats HPRIM : l'anomalie est celle du biologiste, le partiel se voit, le texte est lisible

**Repos**: api-mail, client-mobile, client-angular
**Dependencies**: task-390 (résultats structurés, statut)
**Epic**: E009
**Priorité**: **2** — depuis task-390, une valeur HPRIM hors de ses bornes sans indicateur du laboratoire est signalée comme anomalie : elle entre dans la file « à acquitter » et dans « anormaux non lus », alors que le biologiste ne l'a pas jugée anormale. Le même examen reçu en CDA ne le serait pas. Le statut « partiel » n'est visible nulle part, et le texte du compte rendu montre les lignes techniques du laboratoire.

> **Origine.** Séance `/po` du 2026-10-23 (parsing HPRIM), suite de task-389 et task-390.
> Arbitrages rendus le 2026-10-26 (voir « Décisions actées »).
>
> **Révision de la décision 1 de task-390** (humain, 2026-10-26).
> - task-390 avait retenu : « indicateur du laboratoire, sinon valeur hors de ses bornes ». La règle s'inspirait de Weda, mais Weda n'en fait qu'un **style d'affichage**, rouge, activé par une préférence de l'utilisateur (`userPreferenceHprim.Anormale`). Ni alerte, ni acquittement.
> - Décision : **le jugement d'anomalie appartient au biologiste.** Seul l'indicateur du laboratoire fait l'anomalie, exactement comme le code d'interprétation d'un CR-BIO CDA.
>
> **Pas de remplacement du partiel** : task-391 a été réduite au signal doublon. Le partiel et son complété restent tous deux visibles ; le partiel se reconnaît à sa mention « partiel ».

## Ce qui est établi

- **CDA** (`CdaParsingService`) : un résultat est signalé **seulement** si le laboratoire a posé un code d'interprétation `L`, `H`, `A`, `LL`, `HH` ou `AA`. L'intervalle de référence est affiché, jamais comparé à la valeur. Les clients colorent une ligne d'après ce code (critique, anormal, flèche ↑ ↓).
- **HPRIM depuis task-390** (`HprimStructuredResults`) : un résultat est signalé si l'indicateur du laboratoire (champ 8) est l'un de ces codes. **Sinon**, il est signalé dès qu'une valeur numérique sort de ses bornes. Cette seconde branche fait entrer le document dans la file « à acquitter » (task-170) et compte le patient dans « anormaux non lus ». Les clients, eux, n'affichent pas d'anomalie sans code : le médecin voit un document « à acquitter » sans valeur anormale visible.
- Le champ 8 d'une ligne `RES|` est l'**équivalent exact** du code d'interprétation CDA : même table HL7 (N, L, H, LL, HH, A, AA).
- **Statut** (task-390) : P partiel, F final, C corrigé, persisté et exposé ; aucun client ne l'affiche.
- **Texte du document HPRIM** : il contient encore le bloc technique du laboratoire (`****LAB****`, lignes `TEX|` et `RES|`).
- **Frise de biologie du patient** (mobile et weda2, `biology-timeline`) : les courbes se forment par section, puis par code + libellé + unité.
  - Tous les résultats HPRIM sont dans la section « Résultats de laboratoire ». Un CR-BIO CDA porte en pratique ses propres sections (Biochimie, Hématologie…) : un HPRIM et un CDA ne partagent pas de courbe.
  - **Aucun changement dans cette US** (humain, 2026-10-26) : une courbe par laboratoire couperait l'historique d'un patient qui change de laboratoire, pour un risque de fusion à tort très faible (même code, même libellé et même unité pour deux examens différents).
- **Tableau de biologie du détail** (mobile et weda2) : il affiche déjà les résultats HPRIM (valeur, unité, bornes), avec le même composant que le CR-BIO CDA.

## Décisions actées (humain, 2026-10-26)

1. **Anomalie = indicateur du laboratoire, seulement.** Une valeur hors de ses bornes sans indicateur n'est **pas** une anomalie : ni mise en évidence, ni acquittement, ni « anormaux non lus ». La valeur et ses bornes restent affichées côte à côte : le médecin voit l'écart et en juge. Le HPRIM se comporte exactement comme le CDA.
2. **Détail d'un document HPRIM** :
   - le **tableau des résultats** d'abord : valeur, unité, bornes, anomalie du laboratoire mise en évidence, mention « partiel » ;
   - **puis le texte** du compte rendu, sans les lignes techniques ;
   - le PDF reste accessible comme pour un CDA.
3. **Acquittement** : comme un CR-BIO CDA. Un document HPRIM entre dans la file « à acquitter » quand le **laboratoire** a signalé au moins une valeur.
4. **Hors périmètre** :
   - un repère visuel neutre « hors intervalle de référence » (le rouge de Weda) n'est pas livré. S'il est demandé, ce sera une **préférence de l'utilisateur**, dans une US à part ;
   - les courbes de la frise ne changent pas (pas de courbe par laboratoire). Un cas réel de fusion à tort sera traité avec l'exemple sous les yeux.

## Objective

Le médecin lit un résultat HPRIM comme un CR-BIO CDA :
- seules les anomalies posées par le biologiste sont signalées, mises en évidence et à acquitter ;
- le résultat partiel est reconnaissable ;
- le texte est lisible.

### Règles métier

- **Anomalie** (décision 1) : un résultat HPRIM est signalé si, et seulement si, son indicateur vaut `L`, `H`, `A`, `LL`, `HH` ou `AA`. Les bornes ne font jamais une anomalie.
  - **`N`, vide ou inconnu** (`*`, `+`…) : le résultat n'est pas signalé.
  - **Mise en évidence** : identique au CDA (critique, anormal, flèche).
- **Tableau des résultats** (détail du document, mobile et weda2) : une ligne par résultat, avec libellé, valeur, unité, bornes et seconde valeur si elle existe.
  - **« Partiel »** sur chaque résultat partiel, et en tête du document s'il en porte au moins un.
  - **Le code local du laboratoire** n'est jamais présenté comme un code LOINC (libellé « code labo »).
- **Texte du compte rendu** : affiché sous le tableau, tel que le laboratoire l'a mis en forme, sans les lignes techniques. Un HPRIM sans résultat structuré n'affiche que son texte.
- **Frise du patient** : courbes inchangées ; un point « partiel » est marqué.
- **« Anormaux non lus » et acquittement** : règles existantes du CDA, inchangées. Seul l'indicateur du laboratoire y fait entrer un résultat HPRIM.
- **Partiel et complété** : tous deux visibles et acquittables ; aucun remplacement.
- **BAL déléguée** (règle 14) :
  - le tableau et le texte d'un HPRIM délégué s'affichent de la même façon, lus en direct à l'ouverture du message ;
  - pas d'acquittement, ni d'entrée dans « anormaux non lus » ou dans la frise (task-398 inchangé) ;
  - rien n'est persisté chez le délégataire.

## Definition of Done

- [ ] Build et tests verts : api-mail, client-mobile, client-angular
- [ ] **Anomalie (api-mail)** : la comparaison aux bornes est retirée de la lecture `RES|`. Les tests unitaires de task-390 qui la portaient sont remplacés :
  - indicateur `L`/`H`/`A`/`LL`/`HH`/`AA` → signalé ;
  - `N`, vide ou inconnu → non signalé, même hors bornes
- [ ] **Test d'intégration (règle 1b)**. Un HPRIM rattaché porte deux valeurs : une hors bornes sans indicateur, une signalée `H` par le laboratoire.
  - **Pour `GET biology/patients/{id}`** : seule la valeur `H` porte `IsFlagged`, lu dans la réponse réelle.
  - **Pour `GET biology/abnormal-unread`** : le patient y figure avec la seule valeur `H`.
  - **Cas d'échec** : un HPRIM dont toutes les valeurs sont hors bornes sans indicateur → le patient n'est pas dans « anormaux non lus », et le document n'est pas dans la file « à acquitter ».
  - Vu rouge sur le code de task-390.
- [ ] **Test d'intégration (règle 1b) pour le contenu d'un message HPRIM** : le texte du document ne contient plus les lignes `****LAB****`, `TEX|`, `RES|`, et garde le texte du compte rendu ; vu rouge
- [ ] Tests de composant (mobile et weda2) :
  - tableau des résultats HPRIM : valeur `H` mise en évidence comme un CDA ; valeur hors bornes sans indicateur **non** mise en évidence ; mention « partiel » ; seconde valeur ; « code labo » ;
  - frise : un point « partiel » est marqué
- [ ] Scénario **E2E-BIO-003** ajouté dans Api/Mail/e2e/scenarios.yml (version 1), requis sur mobile et angular, implémenté dans les deux clients. Seed e2e d'un HPRIM synthétique avec une valeur signalée `H` par le laboratoire, une valeur hors bornes sans indicateur et un résultat partiel. Attendu : « ouvrir un résultat HPRIM ; seule la valeur signalée par le laboratoire est mise en évidence ; la mention partiel est visible ; l'acquitter »
- [ ] **BAL déléguée — test d'intégration** (banc de délégation de task-397) :
  - le détail d'un HPRIM délégué renvoie un texte sans lignes techniques, et seules les valeurs signalées par le laboratoire portent `IsFlagged` ;
  - « anormaux non lus » du délégataire reste vide ;
  - la base du délégataire ne contient aucune ligne pour ce message ;
  - vu rouge (règle 1b)
- [ ] La doc d'EPIC E009 corrige la règle d'anomalie de task-390 (v1.113) : l'anomalie est celle du biologiste
- [ ] Aucune donnée de santé en clair dans les journaux (valeurs, libellés, traits patient)
- [ ] data-testid sur tout élément interactif ajouté ; aucune chaîne en dur (i18n)

## Manual Test Plan

Lancer l'AppHost, puis le mobile (`cd Client/Mobile && npm start`) et weda2. Se connecter en Cyril par PSC.
Messages de test : HPRIM synthétiques (`.eml` déposés dans la Réception de Cyril), dont un avec :
- une valeur hors bornes **sans** indicateur ;
- une valeur signalée « H » par le laboratoire ;
- une valeur qualitative ;
- un résultat partiel.

1. Ouvrir le message :
   - le tableau vient en tête, et **seule** la valeur « H » est mise en évidence (flèche ↑, comme un CR-BIO CDA) ;
   - la valeur hors bornes sans indicateur s'affiche normalement, avec ses bornes à côté ;
   - le résultat partiel porte « partiel », en tête du document aussi ;
   - le code est présenté comme « code labo ».
2. Sous le tableau, le texte du compte rendu s'affiche **sans** les lignes `****LAB****`, `TEX|`, `RES|`. Le PDF reste accessible.
3. Le document est dans la file « à acquitter » (à cause de la valeur « H ») ; l'acquitter.
4. Un second HPRIM dont les seules valeurs anormales sont hors bornes **sans** indicateur : il n'est **pas** dans la file « à acquitter », et une fois rattaché, son patient n'est pas dans « anormaux non lus ».
5. Rattacher le premier document à une fiche : le patient apparaît dans « anormaux non lus » avec la valeur « H ».
6. Frise de biologie du patient : le point du résultat partiel est marqué « partiel ».
7. **BAL déléguée** : ouvrir le même HPRIM dans la boîte de Virginie, en Cyril. Le tableau et le texte s'affichent, sans acquittement ; « anormaux non lus » de Cyril reste vide.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : biologie médicale (réception en médecine de ville)
- **Vague Ségur** : hors Ségur — HPRIM est un format historique ; le CR-BIO CDA reste prioritaire
- **Exigences DSR honorées** : non applicable — aucune exigence DSR sur le HPRIM.
  - Règles de prudence : l'anomalie est celle validée par le biologiste, jamais déduite par la plateforme.
  - Codes locaux jamais présentés comme LOINC ; une courbe HPRIM n'est jamais mêlée à une courbe LOINC (sections distinctes).
- **INS** : non applicable — aucun changement d'identité ; « anormaux non lus » ne porte que sur les documents rattachés (task-390)
- **Authentification PS** : inchangée — PSC / e-CPS de la session de messagerie
- **Habilitations** : inchangées. BAL déléguée : lecture seule sans stockage, sans acquittement (règle 14, task-398)
- **Interop CI-SIS** : non applicable — HPRIM Santé ; indicateur d'anomalie sur la table HL7 commune avec le CDA (ObservationInterpretation)
- **Tracé PGSSI-S** : l'acquittement suit le tracé existant (task-170) ; aucun nouvel évènement
- **Consentement patient** : non applicable — aucun envoi vers le DMP ni Mon Espace Santé
- **Référentiels métier** : codes d'examen locaux au laboratoire (ni LOINC ni NABM) ; indicateurs HL7 (N, L, H, LL, HH, A, AA)
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangée — affichage de données déjà reçues et conservées
