# todo-task-391.md — Rattacher un résultat HPRIM : suggestion de patient, remplacement du partiel, signal doublon

**Repos**: api-mail, dtos-mss, client-mobile, client-angular
**Dependencies**: task-389 (le document HPRIM existe, dans la file « à intégrer »), task-390 (résultats structurés et statut partiel)
**Epic**: E009
**Priorité**: **2** — un résultat HPRIM reste aujourd'hui dans la file « à intégrer ». Un partiel et son complété restent côte à côte, et un même fichier reçu deux fois donne deux documents. Le médecin peut le rattacher, mais rien ne range les versions d'une même demande du laboratoire.

> **Origine.** Séance `/po` du 2026-10-23 (parsing HPRIM dans api-mail), suite de task-389 et
> task-390. Arbitrages rendus le 2026-10-26 (voir « Décisions actées »).
>
> **Suite de l'EPIC** : task-392 (affichage des résultats, acquittement, alerte, E2E-BIO-003).

## Ce qui est établi

- **Rattachement existant** (task-012, task-137, task-331) : `POST medical-documents/{id}/attach-patient`.
  - Le médecin choisit une fiche **existante**, jamais créée depuis le rattachement (garde-fou métier).
  - La boîte de comparaison visuelle (weda2 et mobile) propose des candidats classés par similarité des traits (`GET patients/match`). À défaut, elle passe par la recherche par nom (`GET patients/search`).
- **Le document HPRIM porte les traits de l'en-tête** (task-389) : nom, prénom, date de naissance. Il n'a pas d'INS : il n'est **jamais** rattaché automatiquement (task-176).
- **Doublons et versions à la réception** : aucun pour un document sans INS (task-193, décision 6 de task-389). Le rapprochement a été **reporté au rattachement**, contre les documents HPRIM du dossier choisi par le médecin.
- **Mécanismes existants à réutiliser** :
  - le signal doublon (`DuplicateOfId`, bandeau et décision du médecin, task-013) ;
  - le remplacement de version (`SupersededByDocumentId`, chaîne des versions, task-034).
  - Un document remplacé quitte le dossier patient et les alertes, et reste consultable dans la chaîne des versions.
- **Statut des résultats** (task-390) : P partiel, F final, C corrigé, par ligne `RES|`.
- **En-tête HPRIM** : le n° de dossier du laboratoire est le champ 9. **task-389 ne le conserve pas** : cette US doit le garder pour reconnaître la demande.

## Décisions actées (humain, 2026-10-26)

1. **Même demande du laboratoire** = même laboratoire, même n° de dossier **et** même date de résultat.
2. **Partiel remplacé automatiquement**. Le partiel et le complété de la même demande sont rattachés au même patient, dans n'importe quel ordre. Le partiel est alors remplacé par le complété, comme une nouvelle version de CDA :
   - il quitte le dossier et les alertes ;
   - il reste consultable dans la chaîne des versions.
3. **Même fichier reçu deux fois** et rattaché au même patient : le **signal doublon** existant (task-013) s'affiche, et le médecin garde ou écarte. Rien n'est masqué sans lui.
4. **Parcours client** : la boîte de rattachement (mobile et weda2) affiche les traits d'un document HPRIM et son libellé « HPRIM ». Le remplacement du partiel se voit dans le dossier. Nouveau scénario **E2E-BIO-002**, requis sur les deux clients.

## Objective

Rattacher un résultat HPRIM à un patient range ses versions : la suggestion par traits guide le choix de la fiche, le complété remplace le partiel de la même demande, et un même fichier rattaché deux fois est signalé comme doublon.

### Règles métier

- **Suggestion de patient** : la boîte de rattachement montre les traits de l'en-tête HPRIM face aux candidats classés par similarité. Le document est désigné comme un résultat de laboratoire HPRIM, avec son laboratoire et sa date. Sans candidat, le médecin passe par la recherche par nom, comme pour un CDA.
- **Pas de rattachement automatique**, même avec un seul candidat à 100 %.
- **Clé de la demande** (décision 1) : laboratoire + n° de dossier + date du résultat, lus dans l'en-tête et conservés avec le document. Un document dont l'en-tête n'a pas de n° de dossier n'est rapproché de rien.
- **Rapprochement au rattachement, et seulement contre le dossier choisi** : il ne porte que sur les documents HPRIM déjà rattachés à **ce** patient. Un document d'un autre patient, ou encore à intégrer, n'est jamais touché.
- **Document partiel** : il porte au moins un résultat de statut « partiel ».
- **Remplacement** (décision 2) : un document **non partiel** de la même demande remplace le partiel, que le partiel ait été rattaché avant ou après lui.
  - Le partiel quitte le dossier, la biologie du patient, « anormaux non lus » et la file « à acquitter ».
  - Il reste lisible dans la chaîne des versions.
  - Deux partiels de la même demande : le plus récent remplace le plus ancien.
- **Hors périmètre de cette US** : un résultat **corrigé** face à un final de la même demande. Les deux restent visibles ; rien n'est masqué sans décision du médecin.
- **Doublon** (décision 3) : même demande et même contenu → signal doublon existant (task-013). Le médecin garde ou écarte.
- **Détacher** un document remplaçant restaure le document qu'il avait remplacé (comportement de la chaîne de versions du CDA).
- **BAL déléguée** (règle 14) : un document délégué n'est **jamais** rattachable.
  - Aucun geste de rattachement ni de suggestion de patient (task-398 inchangé).
  - Aucune recherche de patient n'est faite avec ses traits.
  - Rien n'est persisté chez le délégataire.

## Definition of Done

- [ ] Build et tests verts : api-mail (et dtos-mss si le contrat change), client-mobile, client-angular
- [ ] Le n° de dossier du laboratoire est conservé avec le document HPRIM (migration de la base mail si nécessaire, nullable, sans effet sur les documents existants)
- [ ] ≥ 1 test unitaire par règle :
  - clé de la demande (même labo, même n° de dossier, même date / l'un des trois différent / n° de dossier absent) ;
  - document partiel ou non ;
  - partiel remplacé (complété rattaché après, puis avant) ;
  - deux partiels ;
  - corrigé face à un final (rien n'est remplacé) ;
  - même contenu → doublon
- [ ] Test d'intégration de bout en bout (règle 1b) pour `POST attach-patient` :
  - **nominal** : un partiel est rattaché, puis le complété de la même demande au même patient. La réponse réelle du dossier et de la biologie du patient ne montre plus que le complété, et la chaîne des versions du complété montre le partiel ;
  - **ordre inverse** : même résultat ;
  - **cas d'échec** : même n° de dossier mais autre laboratoire, ou autre date → rien n'est remplacé ;
  - **autre patient** : le complété rattaché à un autre patient ne remplace rien ;
  - vu rouge
- [ ] Test d'intégration : même fichier reçu deux fois et rattaché au même patient → le second porte le signal doublon dans la réponse réelle ; aucun n'est masqué
- [ ] Test d'intégration : le partiel remplacé n'est plus dans « anormaux non lus » ni dans la file « à acquitter »
- [ ] Test d'intégration : détacher le complété fait revenir le partiel dans le dossier
- [ ] **BAL déléguée — test d'intégration** (banc de délégation de task-397) :
  - un HPRIM délégué n'expose aucun identifiant rattachable ;
  - la base du délégataire ne contient aucun document, aucune ligne de biologie ni aucun n° de dossier pour ce message ;
  - vu rouge (règle 1b)
- [ ] Boîte de rattachement (mobile et weda2) : un document HPRIM affiche ses traits, son laboratoire, sa date et le libellé « HPRIM » ; test de composant (rendu et choix d'un candidat)
- [ ] Scénario E2E-BIO-002 ajouté dans Api/Mail/e2e/scenarios.yml (version 1), requis sur mobile et angular, implémenté dans les deux clients. Seed e2e d'un partiel et de son complété (même demande, synthétiques et anonymisés). Attendu : « rattacher le partiel puis le complété au même patient ; le dossier ne montre que le complété, le partiel est dans ses versions »
- [ ] Aucune donnée de santé en clair dans les journaux : ni trait patient, ni n° de dossier, ni valeur de résultat
- [ ] data-testid sur tout élément interactif ajouté ; aucune chaîne en dur (i18n)

## Manual Test Plan

Lancer l'AppHost, puis le mobile (`cd Client/Mobile && npm start`) et weda2. Se connecter en Cyril par PSC.
Messages de test : deux HPRIM synthétiques de la même demande (même laboratoire, même n° de dossier, même date), l'un avec un résultat partiel, l'autre complet. Les générer comme pour task-389 (`.eml` déposés dans la Réception de Cyril).

1. Ouvrir le partiel, puis « Rattacher ». La boîte montre les traits du HPRIM (nom, prénom, naissance), le laboratoire, la date, « HPRIM » et les candidats classés. Choisir une fiche existante.
2. Rattacher le complété à la **même** fiche. Le dossier du patient ne montre plus que le complété ; sa chaîne des versions montre le partiel.
3. Refaire en rattachant d'abord le complété, puis le partiel : même résultat.
4. Détacher le complété : le partiel revient dans le dossier.
5. Déposer deux fois le même HPRIM et rattacher les deux à la même fiche : le second porte le bandeau doublon, et le médecin peut garder ou écarter.
6. Rattacher le complété à une **autre** fiche : le partiel de la première fiche n'est pas remplacé.
7. **BAL déléguée** : ouvrir un HPRIM dans la boîte de Virginie en Cyril. Aucun geste de rattachement ni de suggestion de patient n'est proposé.
8. Seq : aucun trait patient, aucun n° de dossier, aucune valeur de résultat.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : biologie médicale (réception en médecine de ville)
- **Vague Ségur** : hors Ségur — HPRIM est un format historique hors CI-SIS ; le CR-BIO CDA reste prioritaire (task-389, décision 4)
- **Exigences DSR honorées** : identito-vigilance — aucun rattachement sans le choix explicite du médecin, aucune fiche créée depuis le rattachement, rapprochement limité au dossier du patient choisi
- **INS** : non applicable — le HPRIM ne porte pas d'INS ; les traits ne servent qu'à **suggérer** une fiche, jamais à rattacher (task-176)
- **Authentification PS** : inchangée — PSC / e-CPS de la session de messagerie
- **Habilitations** : documents de la boîte du médecin. BAL déléguée : aucun rattachement possible (règle 14, task-398)
- **Interop CI-SIS** : non applicable — HPRIM Santé (en-tête à positions fixes, lignes `RES|`)
- **Tracé PGSSI-S** : rattachement et détachement déjà tracés (task-012) ; le remplacement d'un partiel suit le tracé du remplacement de version existant ; aucun nouvel évènement
- **Consentement patient** : non applicable — aucun envoi vers le DMP ni Mon Espace Santé
- **Référentiels métier** : aucun (codes d'examen locaux au laboratoire, task-390)
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangée — même traitement (rattachement de résultats reçus) ; le n° de dossier du laboratoire est une donnée du compte rendu déjà reçu, conservée avec lui
