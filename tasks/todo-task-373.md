# todo-task-373.md — Le dossier patient ne montre que les documents, résultats et choix de ce patient

**Repos**: client-angular, api-mail
**Dependencies**: task-371 (fenêtre du document et chargements annulables)
**Epic**: E009
**Single frontend**: true
**Priorité**: **1** — la fiche d'un patient affiche le document, la biologie et la synthèse clinique d'un autre patient ; des résultats sont présentés avec une mauvaise unité ; l'opposition affichée et modifiée peut être celle d'une autre fiche.

> **Origine.** Audit de détection de bugs du client Angular du 2026-10-13
> (`Docs/audits/client-angular-audit-bugs-20261013.md`, **ANG-20 ✔, ANG-50, ANG-51, ANG-52, ANG-53, ANG-54**).

## Ce qui est établi

- **ANG-20** — `patient-timeline.component.ts:121-129` : `allDocuments` verse dans la chronologie **tous** les documents de chaque mail (`getEmailContent`, qui ne filtre pas par patient — `MailRepository.cs:1253-1334`), sans regarder `doc.patientId`. Un mail à deux CDA rattachés à X et à Y : la fiche de X montre le document, la biologie et la synthèse de Y. Les décisions « suppression acceptée », « supplanté » et « doublon » sont aussi annulées à l'affichage. La route de contenu est en cache 15 min.
- **ANG-50** — `mss-patient.component.html:142-143`, `mss-api.service.ts:1241-1243, 1307-1382` : la fiche est relue par INS (`POST /Patients/resolve`) au lieu de son handle. Un matricule connu dans deux domaines (task-331) donne deux fiches : chronologie et opposition de l'autre fiche. Le front réintroduit le mélange AUD-34.
- **ANG-51** — `biology-timeline.component.ts:655-671, 377-385` : une ligne par `code|nom`, unité et normes prises sur le premier résultat ; tendances calculées entre unités différentes (g/L et mmol/L).
- **ANG-52** — biologie et synthèse calculées sur les seules pages de mails chargées ; la période choisie automatiquement masque le résultat le plus ancien (arithmétique en jours contre coupure en mois).
- **ANG-53** — `patient-card.component.ts:157-180`, `patient-consent.component.ts:97-121` : un échec d'enregistrement de l'opposition laisse la case cochée et le badge « Opposition active », sans message.
- **ANG-54** — `patient-attachment-dialog.component.ts:103-158, 292-307` : une réponse de candidats en retard s'affiche sous les traits d'un autre document ; « Rattacher » (sans confirmation) rattache au patient d'un autre.

## Objective

Que la fiche d'un patient ne présente **que** les documents, résultats et décisions qui lui appartiennent, avec l'unité et la norme de chaque résultat, et que les choix du médecin sur ce patient (opposition, rattachement) soient appliqués à **cette** fiche et reflètent l'état réel du serveur.

### Périmètre

1. **Documents du dossier servis par le serveur** depuis les documents actifs du patient (`ActiveDocumentsForPatient`), par page, au lieu du contenu complet des mails.
2. **Fiche désignée par son handle** dans la chronologie et l'opposition (les routes existent) ; domaine affiché dans les résultats de recherche quand deux fiches partagent un matricule.
3. **Biologie** : unité dans la clé de ligne (ou tendances seulement sur une unité homogène), unité et norme affichées par valeur ; données de biologie et de synthèse indépendantes de la pagination des mails ; période calculée avec la même arithmétique que la coupure, sans écraser le choix du médecin.
4. **Opposition** : retour à l'état précédent et message en cas d'échec ; état et date relus depuis la réponse du serveur.
5. **Rattachement manuel** : réponse ignorée si le document n'est plus celui du dialogue.

## Definition of Done

- [ ] Build et tests verts : weda2, api-mail
- [ ] Test d'intégration de bout en bout pour la route des documents du dossier patient : un mail à deux CDA rattachés à X et à Y — la réponse pour X ne contient que le document de X ; un document « suppression acceptée » n'y figure pas (lus dans la réponse réelle), vu rouge (règle 1b)
- [ ] Tests unitaires et de composant rouges d'abord :
  - [ ] la chronologie de X n'affiche aucun document dont `patientId` ≠ X
  - [ ] la chronologie et l'opposition sont chargées par le handle de la fiche, jamais par l'INS
  - [ ] deux résultats du même analyte en g/L et en mmol/L ne partagent ni ligne ni tendance ; chaque valeur affiche son unité
  - [ ] un résultat de 104 jours est visible avec la période choisie automatiquement
  - [ ] échec du `PUT` d'opposition : la case revient à son état, un message s'affiche
  - [ ] réponse de candidats du document A arrivée après l'ouverture sur B : ignorée
- [ ] Scénario E2E-PATIENT-003 « La fiche d'un patient ne montre pas les documents d'un autre patient du même mail » ajouté (angular `requis` ; mobile : `non-applicable` si la vue patient n'existe pas sur mobile, à confirmer au `/start`)
- [ ] Trou du filet : ligne dans `conventions/e2e.md`
- [ ] Aucune INS, NIR ni contenu CDA dans les journaux ou les URL

## Manual Test Plan

1. Recevoir un mail portant deux CDA sans INS ; rattacher le premier à X, le second à Y. Ouvrir la fiche de X → seul le document de X apparaît (documents, biologie, synthèse). Idem pour Y.
2. Patient dont la glycémie vient de deux laboratoires (g/L et mmol/L) → deux lignes, chacune avec son unité ; aucune tendance mêlant les deux.
3. Cocher l'opposition MSSanté avec le réseau coupé → la case se décoche et un message d'erreur s'affiche.
4. Deux fiches de même matricule : ouvrir la seconde → ses documents et son opposition s'affichent, pas ceux de la première.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur — correctif d'identito-vigilance de l'affichage du dossier
- **Exigences DSR honorées** : identito-vigilance (un document n'est présenté que dans le dossier du patient auquel il est rattaché)
- **INS** : utilisée seulement comme trait de recherche ; la fiche est désignée par son handle (INS hors des URL, task-184) ; aucun changement de statut INS
- **Authentification PS** : inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : CDA r2 (affichage) ; résultats de biologie codés LOINC — l'unité devient partie de l'identification d'une série
- **Tracé PGSSI-S** : modification de l'opposition tracée comme aujourd'hui ; aucune trace nouvelle
- **Consentement patient** : opposition à l'envoi vers Mon Espace Santé — l'état affiché devient celui du serveur
- **Référentiels métier** : LOINC (biologie), UCUM (unités)
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : inchangé

## Timings

*(généré par `tools/timing/report.sh --task task-373 --sync` — ne pas éditer à la main)*

| Étape | Statut | Durée | Builds | Tests | Scans | Détail |
|---|---|---|---|---|---|---|
| /start | failed | 4.4 s | — | — | — | dependance task-371 non terminee (todo) |
| **Total cycle** | | **4.4 s** | **0 (0.0 s)** | **0 (0.0 s)** | **0 (0.0 s)** | |
