# todo-task-250.md — Deux médecins qui correspondent avec le même confrère perdent une écriture

**Repos**: api-mail
**Epic**: E015
**Single frontend**: true
**Dependencies**: aucune
**Priorité**: **2** — rare aujourd'hui (1 occurrence sur 133 214 requêtes), mais
c'est une **écriture perdue**, pas une lenteur : elle est silencieuse et sa
probabilité **croît avec la population**.

## Objective

Qu'une mise à jour concurrente d'un contact praticien ne se perde plus.

## Ce qui est établi

Tir local 200 du 2026-08-08, palier 200, une occurrence :

```
DbUpdateConcurrencyException : The database operation was expected to affect
1 row(s), but actually affected 0 row(s)
  ContactRepository.UpdateAsync (ContactRepository.cs:180)
  ← PractitionerContactService.EnrichContactAsync (PractitionerContactService.cs:108)
  ← PractitionerContactService.CreateOrUpdateContactAsync (:51)
```

Deux passages concurrents enrichissent le **même** contact praticien ; le second
ne trouve plus la ligne dans l'état qu'il avait lu, n'affecte aucune ligne, et
lève. L'exception est journalisée puis **avalée** : côté produit, l'enrichissement
du contact est simplement **perdu**, sans que personne ne le sache.

**Pourquoi la fréquence va monter** : le cas se produit quand deux praticiens
correspondent avec le **même** confrère au même moment. À 200 médecins c'est rare ;
la probabilité croît avec le carré de la population, pas linéairement.

## Ce qu'il ne faut PAS présumer

- **Ne pas présumer que c'est bénin parce que c'est rare.** Une donnée d'annuaire
  qui ne se met pas à jour se voit des semaines plus tard, ou jamais.
- **Ne pas présumer que la ligne a été supprimée.** `0 row(s) affected` en
  concurrence optimiste signifie « l'état a changé depuis la lecture » — le plus
  probable est une **écriture concurrente**, pas une suppression. À établir avant
  de choisir entre un `UPSERT` et une relecture sur conflit.

## Definition of Done

- [ ] Une mise à jour concurrente du même contact n'échoue plus silencieusement :
      soit elle est fusionnée (`UPSERT`), soit elle est rejouée sur conflit
- [ ] La stratégie retenue est **justifiée par la cause établie**, pas choisie par
      défaut : quel état a changé, et pourquoi
- [ ] **Test de concurrence** : deux mises à jour simultanées du même contact ;
      l'état final contient les deux enrichissements, ou la règle de préséance est
      explicite et testée
- [ ] Si un cas reste irréconciliable, il est **journalisé comme un conflit
      métier** — jamais avalé
- [ ] Zéro `DbUpdateConcurrencyException` sur un tir 200

## Manual Test Plan

- Depuis deux praticiens du banc, recevoir chacun un message du **même** confrère
  au même moment (deux envois simultanés)
- Vérifier dans les deux boîtes que la fiche du confrère est complète et cohérente
  (nom, spécialité, adresse MSSanté)
- Vérifier dans Seq l'absence de `DbUpdateConcurrencyException`

Données de test synthétiques uniquement.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville (MSSanté — LPS)
- **Vague Ségur** : hors Ségur — correction de robustesse
- **Exigences DSR honorées** : aucune exigence nouvelle ; la US **restaure** la
  fiabilité d'une donnée d'annuaire professionnel
- **INS** : non applicable — il s'agit de contacts **praticiens**, pas de patients
- **Habilitations** : le contact porte un **RPPS** ; une fusion ne doit jamais
  mélanger deux praticiens distincts — c'est le risque fonctionnel n°1 de cette US,
  et il doit être couvert par un test
- **MSSanté** : l'adresse du contact peut être personnelle ou organisationnelle —
  la fusion doit préserver le type
- **Authentification PS / Consentement / Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : un conflit non résolu doit être traçable
- **Hébergement HDS** : sans objet
- **AIPD / impact RGPD** : inchangé
