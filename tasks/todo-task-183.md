# todo-task-183.md — `X-MSS-INS: O` annoncé pour une INS non qualifiée (NIA, OID de test) ; l'OID est perdu à la persistance

**Repos**: api-mail
**Dependencies**: —
**Epic**: E009
**Single frontend**: true

> **Origine** : exploration de bugs `api-mail` du 2026-07-25 (axe métier MSSanté).
> **Sujet d'identito-vigilance — arbitrage humain requis, voir point 4.**

> ### Re-vérification du 2026-08-23 — **toujours pertinente, intégralement**
>
> Chaque preuve rejouée sur `develop` après merge des tasks 226 à 267. Les
> numéros de ligne du bloc « Preuve » ci-dessous datent du 2026-07-25 ; **la
> colonne « au 2026-08-23 » fait foi**.
>
> | Preuve | 2026-07-25 | Au 2026-08-23 | État |
> |---|---|---|---|
> | Qualification par non-vacuité seule | `MssanteHeaderService.cs:185-194` | **`:192-198`** (`hasInsIdentifiers` 192-193, `hasIdentityTraits` 194, `return` 198) | inchangé |
> | OID jamais persisté | « aucune colonne `PatientOid` » | **inchangé** — `PatientOid` n'est écrit qu'en mémoire (`CdaParsingService.cs:219`) et n'existe dans aucune entité | inchangé |
> | Aucune constante d'OID | — | **confirmé** : les quatre OID (`…1.4.8/.9/.10/.11`) n'apparaissent **nulle part** dans le source d'`api-mail` — la valeur n'est donc jamais examinée, ni pour qualifier ni pour rejeter | inchangé |
>
> L'arbitrage humain du point 4 (NIA, OID de test, fusion rétroactive) **reste
> ouvert** et reste le vrai préalable. Le point 1 demeure livrable seul.

## Objective

Rétablir la vérité de l'annonce d'identité INS dans les messages MSSanté émis, et
conserver le **domaine d'identification** (OID) au-delà du parsing.

Deux défauts se composent :

1. **Annonce fausse** — l'en-tête `X-MSS-INS: O`, qui déclare au LPS destinataire
   que le document porte une **INS qualifiée**, est émis dès qu'un identifiant et
   un OID sont *non vides*, sans jamais regarder **quel** OID. Un NIA
   (`1.2.250.1.213.1.4.9`, identité **provisoire**) ou même un OID de **test**
   (`.10` / `.11`) déclenche donc la même annonce qu'un NIR qualifié.
2. **Perte de l'OID** — aucune colonne ne porte l'OID patient (`MailPatient` et
   `MailMedicalDocument` n'ont qu'un `PractitionerOid`). L'identité patient est
   donc clé sur le **matricule nu**, sans son domaine.

**US backend-only (justification)** : conformité d'émission et modèle de données.

### Preuve (état actuel du code)

- `src/Application/Services/Implementation/MssanteHeaderService.cs:185-194`
  (utilisé en `:124-126`) — la « qualification » ne teste que la non-vacuité :
  ```csharp
  var hasInsIdentifiers = !string.IsNullOrWhiteSpace(document.PatientIns)
                       && !string.IsNullOrWhiteSpace(document.PatientOid);
  ```
  La **valeur** de l'OID n'est jamais examinée.
- Côté parsing (`interop-cda`), `INSCode` est renseigné pour les OID NIR **et**
  NIA **et** les OID de test — le dernier identifiant rencontré l'emporte quand le
  document en porte plusieurs.
- Aucune colonne `PatientOid` dans le modèle : l'OID s'arrête au parsing.

Conséquence d'identito-vigilance : deux documents du **même** patient, l'un clé
NIA, l'autre clé NIR, produisent **deux dossiers patients distincts** — l'histoire
du patient est coupée en deux. À l'inverse, un matricule de test identique à un
matricule de production **fusionne deux personnes**.

### Contenu attendu

1. **Qualification par l'OID** : n'annoncer `X-MSS-INS: O` que pour une INS
   réellement **qualifiée** au sens du référentiel — OID NIR
   `1.2.250.1.213.1.4.8`, à l'exclusion du NIA (`.9`, provisoire) et des OID de
   test (`.10`, `.11`). Les traits d'identité restent exigés en complément.
2. **Persistance de l'OID** : porter l'OID patient jusqu'en base et l'inclure dans
   la clé d'identité patient, de sorte qu'un matricule ne soit jamais interprété
   hors de son domaine. Migration FluentMigrator + audit règle 7c.
3. **Refus des OID de test en production** : un document porteur d'un OID de test
   ne doit pas être traité comme une identité réelle. Comportement exact à
   arbitrer (point 4).
4. **Arbitrage humain requis — ouvrir `questions/task-183.md`** :
   - Que doit-il advenir d'un document porteur d'une **INS NIA** (provisoire) :
     rattachement au dossier avec mention du statut, ou reprise manuelle comme
     pour l'absence d'INS (règle task-176) ?
   - Que doit-il advenir d'un document porteur d'un **OID de test** en
     environnement de production : rejet, quarantaine, ou ingestion marquée ?
   - Faut-il **fusionner** rétroactivement les dossiers déjà scindés
     NIA/NIR, et selon quel protocole d'identito-vigilance ?
   Le point 1 (ne plus mentir sur `X-MSS-INS`) est livrable **indépendamment** de
   ces réponses : c'est un correctif de conformité d'émission sans ambiguïté.

### Hors scope

- L'appel au téléservice **INSi** pour qualifier une INS (fonctionnalité absente,
  US produit distincte).
- Le rattachement des documents **sans** INS → task-176.
- La clé de contrôle NIR (Corse `2A`/`2B`, pivot de siècle) → task-193.

## Definition of Done

- [ ] Build passes (0 errors)
- [ ] Tests pass (0 failures, hors flaky pré-existants documentés)
- [ ] Test unitaire paramétré sur l'annonce : OID NIR + traits ⇒ `X-MSS-INS: O` ;
      OID **NIA** ⇒ **pas** `O` ; OID de **test** ⇒ **pas** `O` ; OID inconnu ⇒
      **pas** `O` (ces cas doivent échouer sur le code actuel — le vérifier)
- [ ] Test unitaire : traits d'identité incomplets ⇒ pas d'annonce qualifiée, même
      avec un OID NIR
- [ ] Test unitaire : l'OID patient est persisté et relu (aller-retour complet)
- [ ] Test unitaire : deux documents de même matricule mais d'OID **différents** ne
      sont pas fusionnés dans un même dossier patient
- [ ] Test unitaire : deux documents de même matricule et **même** OID sont bien
      rattachés au même dossier (non-régression)
- [ ] Migration FluentMigrator relue selon la règle 7c ; stratégie de reprise des
      données existantes (OID inconnu rétroactivement) documentée
- [ ] `questions/task-183.md` ouvert avec les 3 arbitrages du point 4
- [ ] Aucune donnée de santé en clair dans les logs (ni matricule INS, ni OID
      associé à un patient identifiable)

## Manual Test Plan

1. Lancer le backend : `cd Api/Mail && dotnet run --project src/AppHost`
2. **Émission — INS qualifiée** : préparer un envoi avec document CDA porteur d'un
   OID **NIR** et des traits complets (données de test anonymisées). Envoyer,
   inspecter les en-têtes du message émis (copie dans Envoyés, ou capture SMTP) →
   `X-MSS-INS: O`.
3. **Émission — NIA** : même envoi avec un OID **NIA** → l'en-tête n'annonce
   **pas** une INS qualifiée. Avant correctif, il annonce `O` à tort.
4. **Émission — OID de test** : même envoi avec un OID de test → pas d'annonce
   qualifiée.
5. **Réception / scission de dossier** : ingérer deux documents du même patient,
   l'un clé NIA, l'autre clé NIR → vérifier le comportement retenu après arbitrage
   (au minimum : les deux ne sont pas silencieusement confondus, et le praticien
   comprend ce qu'il voit).
6. **Non-régression** : un flux nominal NIR de bout en bout (réception,
   rattachement, émission) fonctionne comme avant.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — volets MSSanté et identito-vigilance
- **Exigences DSR honorées** : correctif de conformité sur l'annonce d'identité
  INS dans les échanges MSSanté et sur la gestion du domaine d'identification
- **INS** : **cœur du sujet**. Statut (qualifié / récupéré / provisoire) et OID
  (NIR `1.2.250.1.213.1.4.8`, NIA `1.2.250.1.213.1.4.9`, OID de test) doivent être
  distingués. Aucune annonce de qualification sans OID NIR **et** traits validés
- **Authentification PS** : inchangée (PSC / e-CPS)
- **Habilitations** : inchangées
- **Interop CI-SIS** : CDA r2 en réception ; en émission, en-têtes MSSanté du
  volet transport. Le parsing reste dans `interop-cda`
- **Tracé PGSSI-S** : journaliser le refus d'annonce qualifiée et la détection d'un
  OID de test (évènement technique, **sans** matricule)
- **Consentement patient** : non applicable
- **Référentiels métier** : OID d'autorité d'attribution INS
- **Hébergement HDS** : oui
- **AIPD / impact RGPD** : **à mettre à jour** — un LPS destinataire peut avoir
  classé automatiquement un document au titre d'une INS annoncée qualifiée qui ne
  l'était pas. Qualifier avec le humain la portée (volume de messages émis avec
  `X-MSS-INS: O` sur un OID non-NIR) et l'éventuelle information des destinataires.
