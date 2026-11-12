# ADR-2026-11-11 — Ancrage des états de travail d'un document à son identité stable

- **Statut** : accepté (task-453, EPIC E024)
- **Date** : 2026-11-11
- **Portée** : `api-mail` (base de la boîte). Modèle **obligatoire** pour les états de travail des tasks 454 à 463.

## Contexte

La base d'une boîte tient une ligne `Mails` par message IMAP, et les documents médicaux, leurs résultats de
biologie et les acquittements y étaient rattachés **en cascade** :
`Mails` → `MailMedicalDocuments` → `BiologyAcks` (`ON DELETE CASCADE` de bout en bout).

Or une ligne `Mails` est un **miroir IMAP jetable**. Elle est supprimée puis recréée sous un nouvel `Id` dans trois
cas courants :

1. un déplacement fait **hors de la plateforme** (webmail de l'opérateur, autre client IMAP) : la synchronisation
   purge l'UID disparu, puis ingère le message dans son nouveau dossier ;
2. un **changement d'UIDVALIDITY** : le dossier local est purgé, puis relu ;
3. une **suppression puis une restauration** hors plateforme.

Un acquittement de biologie est la trace de la prise de connaissance d'un résultat. Il disparaissait en silence : le
compte rendu revenait « à acquitter », sans historique ni auteur. Le rattachement manuel d'un document à un patient
(seul possible pour un document **sans INS**) se perdait de la même façon. Le défaut a été prouvé par huit tests
d'intégration rouges sur le code d'avant (task-453, `## Develop log`).

## Décision

### 1. La clé d'identité du document

Un état de travail ne se rattache plus à la ligne `Mails` mais à l'**identité stable du document**,
`DocumentAnchor.Compute` (`mss.mail.Domain.Rules`) :

```
clé = "v1:" + hex( SHA-256( Message-ID + "\n" + identité ) )
identité = "fp:" + ContentFingerprint                           (HPRIM : empreinte du contenu)
         | "cda:" + DocumentId + "|" + SetId + "|" + Version     (CDA)
```

- **Message-ID** : il voyage avec le message, quel que soit son dossier ou son UID, et distingue deux envois du même
  document.
- **CDA** : `DocumentId`, `SetId` **et** `Version`. Une nouvelle version (même `SetId`, `Version` supérieure) a une
  autre clé : c'est un **nouveau document**, qui n'hérite d'aucun acquittement de l'ancienne version (règle de
  supersedence de task-034 inchangée).
- **HPRIM** : l'empreinte du contenu (task-391), son identifiant de document n'étant pas garanti stable.
- **Pas de clé** (et donc pas d'ancrage, comportement d'avant) : message sans `Message-ID`, message de patient
  (format `EMAIL`, identifiant dérivé de l'UID), document sans `DocumentId` ni `SetId`.
- **Haché** : longueur fixe (67 caractères), et ni le `Message-ID` ni l'identifiant du document ne sortent dans un
  journal. Un journal n'en cite qu'un extrait (`DocumentAnchor.Short`, 11 caractères).
- La clé n'est calculée que par le code, à l'ingestion. **Aucune reprise de données** (décision humaine du
  2026-11-12 : bases de test uniquement) : la migration ne modifie que le schéma. Si une reprise devient nécessaire un
  jour, elle recalculera la même clé en SQL (`sha256`, `convert_to`, `encode … 'hex'`), et un test comparera les deux
  définitions ; sinon le préfixe de version change.

### 2. Le schéma

| Table | Changement |
|---|---|
| `MailMedicalDocuments` | `AnchorKey` (nullable, index partiel `IS NOT NULL`), posée à l'ingestion |
| `BiologyAcks` | `AnchorKey` ; `MedicalDocumentId` **nullable**, clé étrangère `SET NULL` (et non plus `CASCADE`) ; index partiel des orphelins (`MedicalDocumentId IS NULL`) |
| `ManualPatientAttachments` (nouvelle) | une ligne par clé (unique) : fiche patient (`CASCADE`), document courant (`SET NULL`), auteur (RPPS, prénom, nom, rôle), instant |

La ligne du document (`PatientId`, `ManualAttachedBy*`) reste ce que lisent les écrans ; la table d'ancrage est ce
qui **survit** à la ligne et qui est ré-appliqué.

### 3. La re-liaison

`DocumentWorkStateRelinker.RelinkAsync(db, clés)` re-relie les états **orphelins** (document disparu) d'une clé au
**seul** document vivant de cette clé :

- **à l'identique** : chaque acquittement garde son `Id`, son action, sa note, ses auteurs et son instant ; seul son
  document change. Le rattachement manuel est ré-appliqué avec sa fiche et son auteur, **devant** le rattachement
  automatique par INS ;
- **deux moments** : à l'ingestion d'un document (des orphelins attendent sa clé), et **après une purge** de lignes
  disparues (`DeleteMailsByUidsAsync`) — la synchronisation ne garantit pas l'ordre des dossiers, et le message a pu
  être lu dans son nouveau dossier avant que sa ligne d'origine soit retirée ;
- **dans la transaction de l'ingestion** ; la trace d'audit n'est émise qu'**après** sa validation.

### 4. Les cas ambigus

Si la clé désigne **plusieurs** documents vivants au moment de la décision (une copie rangée ailleurs et l'original
déplacé, par exemple), **rien n'est re-relié** (doctrine task-193 : dans le doute, ne pas rattacher). Les états
restent conservés, orphelins et invisibles ; la décision est journalisée (avertissement, extrait de clé et nombre de
candidats) et tracée.

### 5. Jamais de perte silencieuse

Un message supprimé pour de bon (corbeille vidée) ne détruit plus ses acquittements : ils restent, rattachés à leur
clé, invisibles tant que le même document ne revient pas. La migration descendante supprime les orphelins, puisque la
colonne redevient obligatoire : c'est la perte que corrige la montée.

### 6. Traçabilité (PGSSI-S, règle 14)

Deux actes **système**, sans personne, famille `HealthDataAccess` (3 653 jours) :
`DocumentWorkStateRelinked` (70) et `DocumentWorkStateRelinkSkipped` (71). Un acte déclaré système par l'appelant le
reste même tracé pendant la requête d'une personne (`AuditService.Impute`) : la re-liaison faite par l'ingestion
qu'une ouverture de dossier a déclenchée n'est pas l'acte de la personne qui a ouvert le dossier. Les acquittements
re-reliés gardent leur auteur réel d'origine (délégataire compris). La trace porte le document et le message, jamais
l'INS ni un contenu.

## Modèle imposé aux tasks 454 à 463

Tout **état de travail** d'un document ou d'un message ajouté par les tasks 454 à 463 (traité, report, attribution,
notes, suivis) suit ce modèle, sans exception :

1. il porte la **clé d'ancrage** (`AnchorKey`, `DocumentAnchor`) de ce qu'il qualifie ;
2. sa clé étrangère vers une ligne miroir (`MailMedicalDocuments`, `Mails`) est **nullable et `SET NULL`**, jamais
   `CASCADE` ;
3. il est **re-relié par `DocumentWorkStateRelinker`** (qui s'étend à la nouvelle table), aux deux moments, avec la
   même règle d'ambiguïté ;
4. un test d'intégration prouve qu'il survit au déplacement hors plateforme (harnais
   `FolderOperationsEndToEndTests.WorkStateAnchoring`), vu rouge.

Un état qui qualifie un **message** sans document (traité, report) ancrera sur le `Message-ID` seul : la
généralisation de `DocumentAnchor` à une identité de message est à faire par la première de ces tasks, dans le même
esprit (clé versionnée, calcul SQL identique pour la reprise).

## Conséquences

- **Aucune reprise** : les documents, acquittements et rattachements manuels déjà en base au moment de la migration
  n'ont pas de clé. Ils gardent leur comportement d'avant (perdus si la ligne du message disparaît). Seuls les
  documents reçus après la migration sont protégés. Accepté par l'humain le 2026-11-12 : aucune production, bases de
  test uniquement.
- Une identité ambiguë laisse le compte rendu « à acquitter » sur les deux copies : c'est voulu, l'acte reste
  conservé et la décision est tracée.
- Hors périmètre : les étiquettes (`MailTags`, recalculées à la ré-ingestion) et la réconciliation des drapeaux IMAP
  posés par un autre client.
