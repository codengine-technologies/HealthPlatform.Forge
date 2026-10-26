# todo-task-392.md — Afficher les résultats d'un HPRIM, les acquitter, les signaler dans « anormaux non lus »

**Repos**: api-mail, dtos-mss, client-mobile, client-angular
**Dependencies**: task-390 (résultats structurés, anomalie, statut)
**Epic**: E009
**Priorité**: **2** — les résultats HPRIM sont lus et rangés (task-390), mais le médecin ne les voit pas encore comme des résultats de biologie : ni tableau, ni mention « partiel », ni anomalie mise en évidence quand le laboratoire ne donne pas d'indicateur. Le widget « anormaux non lus » compte ces valeurs sans les montrer.

> **Origine.** Séance `/po` du 2026-10-23 (parsing HPRIM dans api-mail), suite de task-389,
> task-390. Arbitrages rendus le 2026-10-26 (voir « Décisions actées »).
>
> **Pas de remplacement du partiel** : task-391 a été réduite au signal doublon (humain, 2026-10-26).
> Le partiel et son complété restent tous deux visibles ; le partiel est reconnaissable à sa
> mention « partiel » (règle ci-dessous).

## Ce qui est établi

- **Résultats HPRIM en base** (task-390). Chaque résultat porte :
  - valeur, unité, normes et seconde valeur ;
  - un code local au laboratoire (`BiologyCodeSystems.LaboratoryLocal`), jamais LOINC ;
  - une section unique, « Résultats de laboratoire » ;
  - `IsFlagged`, qui vient de l'indicateur du laboratoire, ou à défaut des normes ;
  - le statut P / F / C.
  - Le laboratoire émetteur est porté par le document (`PractitionerOrganization`).
- **Écarts relevés à la livraison de task-390** :
  - **« Anormaux non lus »** (`BiologyRepository`) ne **liste** que les valeurs à indicateur L/H/A (avertissement) et LL/HH/AA (critique). Une valeur HPRIM hors normes sans indicateur est **comptée** (`AbnormalCount`), mais n'apparaît pas dans la liste : le widget montre le patient sans sa valeur. Un test d'infrastructure fige aujourd'hui cette règle.
  - **Frise de biologie du patient** (mobile et weda2, `biology-timeline`) : les séries se forment par section, code, libellé et unité, **sans** le système de codes ni le laboratoire. Deux laboratoires qui donnent le même code local à deux examens différents fusionneraient.
  - **Mise en évidence d'une anomalie** côté clients : elle part du **code** d'interprétation. Une valeur signalée par les normes, sans code, n'est pas mise en évidence.
  - **Texte du document HPRIM** : il contient encore les lignes techniques du bloc structuré (`****LAB****`, `TEX|`, `RES|`).
- **Acquittement** (task-170, E2E-BIO-001) : tout document portant une valeur signalée, dans la Réception, entre déjà dans la file « à acquitter ». Les documents HPRIM y entrent donc depuis task-390. Le panneau d'acquittement est commun.
- **Partiel et complété** : aucun remplacement (task-391 réduite au signal doublon). Les deux documents restent dans le dossier, la biologie, les alertes et la file « à acquitter ».

## Décisions actées (humain, 2026-10-26)

1. **Séries de la frise** : deux résultats HPRIM appartiennent à la même série s'ils viennent du **même laboratoire**, avec le **même code** et la **même unité**. Une série HPRIM n'est jamais mêlée à une série LOINC.
2. **« Anormaux non lus »** : une valeur hors normes sans indicateur du laboratoire est **listée**, comme une alerte non critique, avec sa valeur et ses normes, et marquée « hors normes ». Les valeurs critiques (LL, HH, AA) restent en tête.
3. **Détail d'un document HPRIM** :
   - le **tableau des résultats** d'abord : valeur, unité, normes, anomalie mise en évidence, mention « partiel » ;
   - **puis le texte** du compte rendu, sans les lignes techniques `****LAB****`, `TEX|` et `RES|` ;
   - le PDF reste accessible comme pour un CDA.
4. **Acquittement** : comme un CR-BIO CDA. Tout document HPRIM portant une valeur signalée entre dans la file « à acquitter », rattaché ou non, et s'acquitte avec le même panneau. Le partiel et son complété y entrent chacun, comme deux comptes rendus.

## Objective

Le médecin lit un résultat HPRIM comme un résultat de biologie :
- un tableau qui met en évidence les valeurs anormales, même quand le laboratoire ne donne pas d'indicateur ;
- la mention « partiel » ;
- une courbe par examen et par laboratoire dans la frise du patient ;
- un acquittement identique à celui d'un CR-BIO ;
- les valeurs hors normes listées dans « anormaux non lus ».

### Règles métier

- **Tableau des résultats** (détail du document, mobile et weda2) : une ligne par résultat, avec libellé, valeur, unité, normes et seconde valeur si elle existe.
  - **Anomalie mise en évidence** dès que le résultat est signalé. Avec un indicateur du laboratoire, l'indicateur est affiché (bas, haut, critique). Sans indicateur, la mention est « hors normes ».
  - **« Partiel »** est affiché sur chaque résultat partiel, et en tête du document s'il en porte au moins un.
  - **Le code local du laboratoire** n'est jamais présenté comme un code LOINC (libellé « code labo »).
- **Texte du compte rendu** : affiché sous le tableau, tel que le laboratoire l'a mis en forme, sans les lignes techniques. Un HPRIM sans résultat structuré n'affiche que son texte.
- **Frise de biologie du patient** (décision 1) : série = laboratoire + code + unité pour un résultat HPRIM ; système de codes + code + unité pour un résultat LOINC. Les deux ne fusionnent jamais. Chaque point garde son statut : un point « partiel » est marqué.
- **« Anormaux non lus »** (décision 2) : les valeurs signalées sans indicateur sont listées comme alertes non critiques, marquées « hors normes ». L'ordre reste : critiques d'abord, puis alertes, puis les plus récentes. Le compte ne change pas.
- **Acquittement** (décision 4) : inchangé, partagé avec le CR-BIO CDA. Un partiel et son complété s'acquittent chacun.
- **BAL déléguée** (règle 14) :
  - le tableau et le texte d'un HPRIM délégué s'affichent de la même façon, lus en direct à l'ouverture du message ;
  - pas d'acquittement ni d'entrée dans « anormaux non lus » ou la frise (task-398 inchangé) ;
  - rien n'est persisté chez le délégataire.

## Definition of Done

- [ ] Build et tests verts : api-mail, dtos-mss (si le contrat change, package publié), client-mobile, client-angular
- [ ] **Contrat** : le laboratoire émetteur d'un résultat est disponible là où la frise forme ses séries. Le libellé « hors normes » d'une valeur signalée sans indicateur est prévu dans « anormaux non lus »
- [ ] **Test d'intégration (règle 1b) pour `GET biology/abnormal-unread`** :
  - **nominal** : une valeur HPRIM hors normes sans indicateur, rattachée, est **listée** dans la réponse réelle, marquée « hors normes », avec sa valeur et ses normes ;
  - une valeur critique du même patient reste en tête ;
  - **cas d'échec** : une valeur dans ses normes n'est pas listée ;
  - vu rouge. Le test d'infrastructure qui figeait l'ancienne règle est mis à jour selon la décision 2
- [ ] **Test d'intégration (règle 1b) pour le contenu d'un message HPRIM** : le texte du document ne contient plus les lignes `****LAB****`, `TEX|`, `RES|`, et garde le texte du compte rendu ; vu rouge
- [ ] **Test d'intégration (règle 1b) pour `GET biology/patients/{id}`** : chaque résultat HPRIM porte son laboratoire émetteur. Deux laboratoires, même code local, même unité → deux séries distinguables dans la réponse réelle ; vu rouge
- [ ] Test d'intégration : un document HPRIM portant une valeur signalée entre dans la file « à acquitter » (rattaché ou non) et en sort une fois acquitté, lu dans la réponse réelle
- [ ] Tests de composant (mobile et weda2) :
  - tableau des résultats HPRIM : valeur hors normes sans indicateur mise en évidence et « hors normes », indicateur affiché, mention « partiel », seconde valeur, « code labo » ;
  - frise : deux laboratoires au même code → deux séries ; HPRIM et LOINC → deux séries ;
  - widget « anormaux non lus » : valeur « hors normes » listée
- [ ] Scénario **E2E-BIO-003** ajouté dans Api/Mail/e2e/scenarios.yml (version 1), requis sur mobile et angular, implémenté dans les deux clients. Seed e2e d'un HPRIM synthétique avec une valeur hors normes sans indicateur et un résultat partiel. Attendu : « ouvrir un résultat HPRIM, voir le tableau avec la valeur hors normes mise en évidence et la mention partiel, puis l'acquitter »
- [ ] **BAL déléguée — test d'intégration** (banc de délégation de task-397) :
  - le détail d'un HPRIM délégué renvoie un texte sans lignes techniques ;
  - « anormaux non lus » du délégataire reste vide ;
  - la base du délégataire ne contient aucune ligne pour ce message ;
  - vu rouge (règle 1b)
- [ ] Aucune donnée de santé en clair dans les journaux (valeurs, libellés, traits patient)
- [ ] data-testid sur tout élément interactif ajouté ; aucune chaîne en dur (i18n)

## Manual Test Plan

Lancer l'AppHost, puis le mobile (`cd Client/Mobile && npm start`) et weda2. Se connecter en Cyril par PSC.
Messages de test : HPRIM synthétiques (`.eml` déposés dans la Réception de Cyril), dont un avec une valeur hors normes **sans** indicateur, une valeur signalée « H », une valeur qualitative et un résultat partiel.

1. Ouvrir le message :
   - le tableau des résultats vient en tête ;
   - la valeur hors normes sans indicateur est mise en évidence avec « hors normes », la valeur « H » avec son indicateur ;
   - le résultat partiel porte « partiel », en tête du document aussi ;
   - le code est présenté comme « code labo ».
2. Sous le tableau, le texte du compte rendu s'affiche **sans** les lignes `****LAB****`, `TEX|`, `RES|`. Le PDF reste accessible.
3. Acquitter le document depuis son panneau d'acquittement. Il quitte la file « à acquitter ».
4. Rattacher le document à une fiche. Dans « anormaux non lus », le patient apparaît avec la valeur « hors normes » listée.
5. Frise de biologie du patient :
   - deux résultats HPRIM du même laboratoire, même code et même unité forment une seule courbe ;
   - un autre laboratoire au même code donne une autre courbe ;
   - une glycémie CDA (LOINC) reste une courbe à part.
6. **BAL déléguée** : ouvrir le même HPRIM dans la boîte de Virginie, en Cyril. Le tableau et le texte s'affichent ; aucun acquittement n'est proposé ; « anormaux non lus » de Cyril reste vide.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : biologie médicale (réception en médecine de ville)
- **Vague Ségur** : hors Ségur — HPRIM est un format historique ; le CR-BIO CDA reste prioritaire
- **Exigences DSR honorées** : non applicable — aucune exigence DSR sur le HPRIM. Règle de prudence : codes locaux jamais présentés comme LOINC, séries jamais mêlées entre laboratoires ou avec le LOINC
- **INS** : non applicable — aucun changement d'identité ; l'alerte « anormaux non lus » ne porte que sur les documents rattachés (task-390)
- **Authentification PS** : inchangée — PSC / e-CPS de la session de messagerie
- **Habilitations** : inchangées. BAL déléguée : lecture seule sans stockage, sans acquittement (règle 14, task-398)
- **Interop CI-SIS** : non applicable — HPRIM Santé ; indicateurs d'anomalie sur la table HL7 commune avec le CDA
- **Tracé PGSSI-S** : l'acquittement suit le tracé existant (task-170) ; aucun nouvel évènement
- **Consentement patient** : non applicable — aucun envoi vers le DMP ni Mon Espace Santé
- **Référentiels métier** : codes d'examen locaux au laboratoire (ni LOINC ni NABM) ; indicateurs HL7 (N, L, H, LL, HH, A, AA)
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangée — affichage de données déjà reçues et conservées
