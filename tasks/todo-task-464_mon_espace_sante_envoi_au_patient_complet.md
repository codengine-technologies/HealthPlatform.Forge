# todo-task-464.md — Mon espace santé : envoi au patient complet

**Repos**: api-mail, dtos-mss, client-angular, client-mobile
**Dependencies**: done-task-460 (lecture des avis de non-remise et des accusés de lecture)
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. Douleur n° 8 (messagerie patient : 2/5). E009-F007 est
fait à environ 10 % ; ses exigences bloquantes sont listées en E009 §6.16 (ENS Mon espace santé v1.3).

> **Origine.** Analyse du 2026-11-11, manque E1. 58 % des généralistes échangent déjà avec leurs patients hors
> consultation (DREES), mais par téléphone et par e-mail non sécurisé.

## Ce qui est établi

Lecture du code au 2026-11-11 :

- **Existe** :
  - adresse `{INS}@patient.mssante.fr` (`PatientMessageHelper`, `PatientContactService`) ;
  - en-tête `X-MSS-MES: FIN` (RG-E009-087) ;
  - en-têtes `X-MSS-INS` et `X-MSS-CODECDA` avec contrôle du domaine NIR ;
  - enveloppe IHE_XDM construite à l'envoi ;
  - garde d'opposition à l'envoi (`PatientOppositionGuard`, 409 puis acquittement) ;
  - repérage des messages entrants du patient ;
  - demande d'accusé de lecture ;
  - garde-fou INS sur mobile, partiel sur le web (task-138).
- **Manque** :
  - **RG-E009-082** : l'adresse n'est pas contrôlée côté serveur depuis une INS qualifiée. `InsValidationService`
    n'est utilisé que par `PatientsController`, pas dans le chemin d'envoi.
  - **RG-E009-084** : rien pour les mineurs (`MailPatient.Birthday` existe).
  - **RG-E009-086** : la limite est globale (`MailOptions.MaxAttachmentSizeBytes` = 10 Mo) et porte sur les octets
    bruts, sans la hausse d'environ 33 % due au base64. Pas de règle propre aux patients.
  - **RG-E009-089** : `MailDto.ReplyTo` existe, mais `SmtpService.SetMessageRecipients` ne le pose jamais.
  - **RG-E009-085** et **RG-E009-088** : non-remise et accusé de lecture MES non exploités. Ils sont lus par
    task-460.

## Objective

Un praticien écrit à son patient dans Mon espace santé **sans erreur d'adressage possible**, sait si son message est
arrivé et a été lu, et reçoit la réponse du patient dans la bonne boîte.

Règles :
- **Adresse sûre (RG-E009-082)** : le **serveur** refuse tout envoi vers une adresse `@patient.mssante.fr` qui n'est
  pas construite depuis l'INS **qualifiée** d'un patient de la boîte. Message au praticien : « L'identité de ce patient
  n'est pas qualifiée : l'envoi vers Mon espace santé est impossible. » Le garde-fou web rejoint celui du mobile.
- **Mineurs (RG-E009-084)** : pour un patient mineur, le message part à **l'adresse du mineur lui-même**, jamais à
  celle d'un représentant légal. La rédaction l'indique (« Patient mineur : le message est déposé dans l'espace santé
  de l'enfant »). Une adresse patient saisie à la main qui ne correspond pas à l'INS du patient du document joint est
  refusée.
- **Taille (RG-E009-086)** : 25 Mo au plus vers un patient, **encodage compris**. La jauge de la rédaction affiche la
  taille réelle. Au-delà, l'envoi est refusé avant de partir, avec le motif.
- **Répondre à (RG-E009-089)** : le praticien peut choisir la boîte où le patient répondra (sa boîte, ou une boîte
  partagée de la structure à laquelle il est rattaché). `Reply-To` est réellement posé.
- **Non-remise (RG-E009-085)** : les motifs MES de task-460 (messagerie fermée, patient non trouvé, adresse invalide,
  taille dépassée) s'affichent sur l'envoi, avec la conduite à tenir.
- **Lecture (RG-E009-088)** : l'accusé de lecture du patient, émis d'office par Mon espace santé, passe le statut à
  « Lu par le patient ».

### Hors périmètre

- Message « résultat normal » au patient.
- Tri des réponses des patients (administratif vers le secrétariat).

## Definition of Done

- [ ] Contrôle serveur de l'adresse patient dans le chemin d'envoi (`SmtpService`), testé ; garde-fou web aligné sur
      le mobile.
- [ ] Règle des mineurs : âge calculé à la date d'envoi depuis `MailPatient.Birthday`, Europe/Paris.
- [ ] Taille calculée encodage compris, limite de 25 Mo propre aux destinataires patients, sans changer la limite
      configurée pour les professionnels.
- [ ] `Reply-To` posé par `SetMessageRecipients` ; choix limité aux boîtes auxquelles la personne est rattachée.
- [ ] Contrat : `ReplyTo` choisi, statut « Lu par le patient » et motifs MES ; paquet DTO publié.
- [ ] Tests unitaires : INS qualifiée, INS non qualifiée, adresse saisie différente de l'INS du document, mineur la
      veille et le jour de ses 18 ans, 24,9 Mo et 25,1 Mo encodés, `Reply-To` posé.
- [ ] **Tests d'intégration de bout en bout (règle 1b)** sur l'envoi (`POST api/v1/Mail/sendmail`) :
      - envoi à un patient à l'INS qualifiée : le message reçu (GreenMail) porte l'adresse de l'INS, `Reply-To` et
        `X-MSS-*` attendus ;
      - cas d'échec : patient à l'INS non qualifiée → refus en `ProblemDetails`, rien n'est envoyé ;
      - cas d'échec : 25,1 Mo encodés → refus ;
      - accusé de lecture MES injecté : « Lu par le patient » lu dans la réponse.
      Vu rouge.
- [ ] Tests de composant (weda2 et mobile), vus rouges par mutation : refus INS non qualifiée, mention mineur, jauge
      25 Mo, choix « Répondre à », statut « Lu par le patient ».
- [ ] **Scénarios e2e**, mobile et angular requis, vus rouges :
      - `E2E-MES-001` v1 : l'envoi à un patient dont l'INS n'est pas qualifiée est refusé avec le motif ;
      - `E2E-MES-002` v1 : un message au patient avec « Répondre à » la boîte du cabinet part avec ce choix, et passe
        « Lu par le patient » quand l'accusé revient.
- [ ] E009 §6.16 mis à jour (RG-E009-082, 084, 085, 086, 088, 089) avec l'état réel, prouvé par les tests.
- [ ] Aucune INS ni adresse patient en clair dans les logs ; `data-testid` ; conventions de libellés.
- [ ] Build et tests verts (api-mail, Dtos, weda2, mobile) ; client-angular : code-only.

## Manual Test Plan

1. Backend et weda2 sur l'environnement de formation, avec un patient de test à l'INS qualifiée, un patient à l'INS
   non qualifiée et un patient mineur.
2. Écrire au patient à l'INS non qualifiée : l'envoi est refusé, avec le motif.
3. Écrire au patient mineur : la rédaction indique que le message est déposé dans l'espace santé de l'enfant.
4. Joindre 26 Mo de fichiers : la jauge passe au rouge et l'envoi est refusé avant de partir.
5. Écrire au patient à l'INS qualifiée avec « Répondre à » la boîte du cabinet. Dans l'espace patient de test, ouvrir
   le message : l'envoi passe « Lu par le patient ». Répondre : la réponse arrive dans la boîte du cabinet.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : V2 — ENS Mon espace santé, messagerie usager (spécification éditeurs v1.3)
- **Exigences DSR honorées** : RG-E009-082 (ECO.2.2.6), RG-E009-084, 085, 086, 088, 089 (ENS MES v1.3 §2, §6, §9)
- **INS** : **INS qualifiée exigée** pour tout envoi à un patient, contrôlée côté serveur ; source : dossier patient de
  la boîte (statut issu de l'INSi) ; OID NIR 1.2.250.1.213.1.4.8 ou NIA 1.2.250.1.213.1.4.9
- **Authentification PS** : PSC (e-CPS), eIDAS substantiel — envoi MSSanté
- **Habilitations** : professionnel rattaché à la boîte sous verdict de l'opérateur ; `Reply-To` limité aux boîtes de
  la personne
- **Interop CI-SIS** : IHE_XDM (CDA R2 joint), en-têtes `X-MSS-*`, RFC 8098 (MDN)
- **Tracé PGSSI-S** : envoi au patient (`MailSend`) au nom de la personne réelle, refus pour INS non qualifiée tracé ;
  `HealthDataAccess`, 3 653 jours
- **Consentement patient** : opposition du patient contrôlée côté serveur, inchangée (task-003, task-154)
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — environnement HDS de production
- **AIPD / impact RGPD** : à mettre à jour — échanges avec les usagers et règles des mineurs
