# Analyse de conformité - Module Messagerie MSSante HealthPlatform

**Date** : Juillet 2025
**Périmètre analysé** : API/Mail (Backend .NET), Client Blazor, Client Angular
**Sources** : Spécification fonctionnelle NOVA Messagerie + REM-MDV-LGC-Va2.xlsx (exigences Ségur V1/V2)

## Contexte

Le logiciel analysé dans ce document est un projet personnel développé par **Pascal Cabanel** en dehors de Weda. Démarré il y a 18 mois, ce projet est proposé à Weda en tant qu'**opportunité d'intégration dans Weda/Nova**. La présente analyse vise à évaluer son niveau de couverture fonctionnelle et de conformité réglementaire (Ségur V1/V2) par rapport aux spécifications cibles du module Messagerie MSSante.

---

# PARTIE 1 - Analyse vs. Spécification fonctionnelle

## 1. Contexte et problème

La spécification identifie 5 limites de Weda Echange :

| Limite identifiée | Réponse du projet | Statut |
|---|---|---|
| **Expérience fragmentée** | Clients Blazor et Angular avec widgets embarquables (MailWidget, MailNotificationWidget, AbnormalBiologyWidget) affichables dans le tableau de bord sans quitter le contexte. | **Couvert** |
| **Classement manuel** | Parsing automatique des documents CDA/IHE-XDM (`CdaParsingService`, `IheXdmProcessingService`) avec extraction des métadonnées patient (INS, nom, prénom, date de naissance, sexe) et rattachement automatique via `MailPatient` et `MailMedicalDocument`. | **Couvert** |
| **Absence de priorisation** | Tags avec `urgencyLevel`, suggestion de tags par IA (`EmailTaggingService`), notifications différenciées par `UrgencyLevel`, résultats biologiques anormaux remontés en priorité. | **Couvert** |
| **Recherche de correspondants fastidieuse** | Annuaire intégré MSSante/RPPS via `AnnuaireSanteService` avec recherche multi-critères. Carnet de contacts local avec favoris. | **Couvert** |
| **Pas de vision organisationnelle** | Modèle `MailboxType` (Personal/Organizational) et `SenderIdentityDto` présents. Gestion multi-boîtes simultanées non encore implémentée. | **Partiellement couvert** |

---

## 2. Vision et principes directeurs

| Principe | Implémentation | Statut |
|---|---|---|
| **Transparence** | Autoconfiguration IMAP/SMTP (`AutoconfigService`), authentification via PSC/Keycloak. L'utilisateur ne gère pas les protocoles. | **Couvert** |
| **Contextualisation** | `MailMedicalDocument` lié à `MailPatient` (via INS). Endpoints par INS pour documents et mails. Pages Patient dédiées (Blazor + Angular). | **Couvert** |
| **Priorisation intelligente** | Tags avec niveaux d'urgence, détection biologie anormale, suggestion IA, résumés IA, notifications temps réel différenciées. | **Couvert** |
| **Multi-persona** | Rôles implicites via `ContactType`. Settings personnalisables. Pas de système de rôles explicite (praticien/secrétaire/coordinateur). | **Partiellement couvert** |
| **Multi-boîtes** | `MailboxType` enum présent. Infrastructure technique mono-connexion IMAP par session. | **Partiellement couvert** |

---

## 3. Personas cibles

| Persona | Couverture | Détail |
|---|---|---|
| **Dr. Sophie (Médecin)** | **Bonne** | Dashboard, alertes biologie, recherche sémantique, chat IA, vue patient, documents médicaux. |
| **Marie (Secrétaire)** | **Partielle** | Gestion contacts, annuaire, dossiers, tags. Manque : vue organisationnelle spécifique, workflow de pré-classement. |
| **Thomas (Coordinateur)** | **Partielle** | Threads de conversation, historique patient, recherche avancée. Manque : tableau de bord de coordination, suivi inter-professionnel. |
| **Patient (Mon Espace Santé)** | **Non couvert** | Aucune intégration Mon Espace Santé / DMP. |

---

## 4. Jobs to be done

### JTBD 1 - Recevoir et traiter les documents médicaux entrants

| Capacité attendue | Statut | Détail |
|---|---|---|
| Classement automatique (INS, CI-SIS) | **Implémenté** | `CdaParsingService`, `IheXdmProcessingService`, `MailMedicalDocument`, `MailPatient`. |
| Reconnaissance automatique de documents | **Implémenté** | Extraction LOINC, catégorie, format, biologie détaillée (`MailMedicalDocumentBiology`), synthèses (`MailMedicalDocumentSummary`). |
| Priorisation par sévérité (CI-SIS + IA) | **Implémenté** | Tags urgence, `EmailTaggingService` IA, `IsFlagged` biologie, `NotificationPayloadDto` avec `UrgencyLevel`. |
| Revue proactive | **Implémenté** | Liste enrichie, tags, filtrage, dashboard avec résumé du jour. |
| Contextuel au dossier patient | **Implémenté** | Widgets embarquables, endpoints par INS, pages Patient dédiées. |
| Alerte temps réel | **Implémenté** | SignalR (`MailHub`) + SSE (`SseNotificationBroker`). Préférences de notification (son, desktop, urgence). |

### JTBD 2 - Transmettre des documents médicaux

| Capacité attendue | Statut | Détail |
|---|---|---|
| Envoi intégré | **Implémenté** | `SmtpService`, composition (Blazor + Angular), `EmailBuildingService`, `DraftService`. |
| Recherche de correspondants intégrée | **Implémenté** | `AnnuaireSanteService` multi-stratégies (RPPS, nom, spécialité, localisation). |
| Envoi vers Mon Espace Santé | **Non implémenté** | Aucun service DMP/MES. |
| Favoris et correspondants fréquents | **Implémenté** | `Contact.IsFavorite`, `lastUsedDate`, groupes de contacts. |
| Suivi d'acheminement | **Partiel** | MDN (`MdnService`) implémenté. Pas de suivi complet envoyé/reçu/lu. |

### JTBD 3 - Gérer des boîtes personnelles et organisationnelles

| Capacité attendue | Statut | Détail |
|---|---|---|
| Boîtes perso + organisationnelles | **Partiel** | Modèle présent (`MailboxType`), implémentation mono-connexion. |
| Vue unifiée ou séparée | **Non implémenté** | Une seule connexion IMAP active. |
| Gestion des droits par rôle | **Non implémenté** | Pas de système de rôles explicite. |
| Délégation de traitement | **Non implémenté** | |

### JTBD 4 - Trouver un correspondant sans friction

| Capacité attendue | Statut | Détail |
|---|---|---|
| Annuaire MSSante + RPPS multi-critères | **Implémenté** | Recherche RPPS, nom, prénom, spécialité, code postal, ville, établissement, filtre `hasMssAddress`. |
| Auto-complétion et suggestions | **Partiel** | Suggestions de recherche, tri par dernière utilisation. Auto-complétion contextuelle (cercle de soins) non explicite. |
| Carnet d'adresses personnel et partage | **Partiel** | Carnet personnel complet (CRUD, favoris, tags, groupes, import, fusion). Partage au niveau cabinet non implémenté. |

---

## 5. Feature map

| # | Feature | Statut | Détail |
|---|---|---|---|
| F1 | Boîte de réception unifiée multi-boîtes | **Partiel** | Boîte complète avec dossiers IMAP, mais mono-boîte. |
| F2 | Classement automatique (INS, CI-SIS) | **Implémenté** | Parsing CDA/XDM, extraction INS/patient/praticien, enrichissement background. |
| F3 | Priorisation / scoring de sévérité | **Implémenté** | Tags urgence, IA tagging, détection biologie anormale, résumés IA. |
| F4 | Widget nouveaux documents dans le dossier patient | **Implémenté** | Widgets Blazor et Angular, page Patient dédiée. |
| F5 | Alertes temps réel (urgence élevée) | **Implémenté** | SignalR + SSE, préférences notification, alertes biologie anormale. |
| F6 | Envoi contextuel depuis tout document Weda | **Partiel** | Composition complète avec PJ, brouillons. Intégration directe LGC hors périmètre. |
| F7 | Envoi vers Mon Espace Santé (DMP/MES) | **Non implémenté** | |
| F8 | Annuaire intégré MSSante + RPPS | **Implémenté** | Multi-stratégies de recherche, parsers dédiés. |
| F9 | Carnet d'adresses (favoris, fréquents) | **Implémenté** | Favoris, groupes, tags, import annuaire, fusion, tri dernière utilisation. |
| F10 | Gestion des rôles et permissions (boîtes orga) | **Non implémenté** | |
| F11 | Suivi d'acheminement | **Partiel** | MDN implémenté. Pas de suivi complet. |
| F12 | Délégation de traitement | **Non implémenté** | |
| F13 | Analyse IA du contenu | **Implémenté** | Chat IA (Semantic Kernel), résumés, tags, recherche sémantique (pgvector), actions IA, amélioration de texte. |

---

## 6. Contraintes et dépendances

| Contrainte | Statut | Détail |
|---|---|---|
| MSSante (IMAP/SMTP sécurisé) | **Implémenté** | MailKit, SSL/TLS, validation certificats (CRL, OCSP). |
| CI-SIS | **Implémenté** | `CdaParsingService` (parsing CDA complet, LOINC, catégories). |
| INS / RPPS | **Implémenté** | INS sur `MailMedicalDocument`/`MailPatient`, RPPS sur `Contact`. |
| Mon Espace Santé / DMP | **Non implémenté** | |
| RGPD / HDS | **Compatible** | Base mono-utilisateur, isolation données, feature flags. |
| API Annuaire RPPS/MSSante | **Implémenté** | `AnnuaireSanteService` avec stratégies multiples. |
| Infrastructure IA/LLM | **Implémenté** | Dual Ollama (on-premise) / OpenAI (cloud), pgvector, Semantic Kernel. |

---

## 7. Métriques de succès

| Métrique | Statut |
|---|---|
| Taux de classement automatique | **Mesurable** (`MailMedicalDocument.PatientId` nullable) |
| Temps moyen d'envoi | **Instrumentable** (logs structurés, télémétrie) |
| Taux d'adoption | **Instrumentable** (feature flags Flagsmith) |
| Satisfaction utilisateur | **Non implémenté** (pas d'enquête in-app) |
| Messages urgents traités dans l'heure | **Mesurable** (`receivedAt` + `IsRead` + `urgencyLevel`) |

---

## 8. Hors périmètre respecté

- Pas de messagerie instantanée (chat interprofessionnel)
- Pas de téléconsultation
- Pas de GED avancée
- Pas de prise de rendez-vous
- Pas de facturation

---

## 9. Risques et mitigations

| Risque | Mitigation |
|---|---|
| Classement auto insuffisant | `EnrichmentStatus` avec retry, IA en assistance, fallback manuel. |
| Latence API annuaire ANS | Stratégies de recherche optimisées, cache Redis (`IResilientCacheService`). |
| Résistance au changement | Mode Online/Offline, settings personnalisables (densité, thème, langue). |
| Contraintes IA sur données de santé | Architecture duale Ollama/OpenAI, feature flags pour désactiver l'IA. |
| Évolution référentiel MSSante | Couche d'abstraction (`IImapClientWrapper`, `MailDataProviderFactory`). |

---

## 10. Jalons indicatifs et couverture

> Méthode d'évaluation : **Implémenté = 100%**, **Partiel = 50%**, **Non implémenté = 0%**.
> Le pourcentage de couverture par phase est la moyenne des features de la phase.

### Phase 1 - Fondations (horizon T3 2026)

| Feature | Description | Statut | Couverture |
|---|---|---|---|
| F1 | Boîte de réception unifiée multi-boîtes | Partiel (mono-boîte fonctionnelle, modèle multi-boîtes présent) | 50% |
| F2 | Classement automatique (INS, CI-SIS) | **Implémenté** (CDA/XDM parsing, enrichissement background, rattachement patient) | 100% |
| F6 | Envoi contextuel depuis tout document Weda | Partiel (composition complète avec PJ/brouillons, intégration LGC hors périmètre) | 50% |
| F8 | Annuaire intégré MSSante + RPPS | **Implémenté** (API FHIR, multi-stratégies, recherche multicritères) | 100% |
| F10 | Gestion des rôles et permissions (boîtes orga) | Non implémenté | 0% |

**Couverture Phase 1 : 60%** (3/5 features au moins partiellement couvertes)

### Phase 2 - Intelligence (horizon T4 2026)

| Feature | Description | Statut | Couverture |
|---|---|---|---|
| F3 | Priorisation / scoring de sévérité (CI-SIS + IA) | **Implémenté** (tags urgence, IA tagging, détection biologie anormale, résumés IA) | 100% |
| F4 | Widget nouveaux documents dans le dossier patient | **Implémenté** (widgets Blazor + Angular, page Patient dédiée) | 100% |
| F5 | Alertes temps réel (urgence élevée) | **Implémenté** (SignalR + SSE, préférences notification, alertes biologie) | 100% |
| F7 | Envoi vers Mon Espace Santé (DMP/MES) | Non implémenté | 0% |

**Couverture Phase 2 : 75%** (3/4 features implémentées)

### Phase 3 - Excellence (horizon T1-T2 2027)

| Feature | Description | Statut | Couverture |
|---|---|---|---|
| F9 | Carnet d'adresses (favoris, fréquents) | **Implémenté** (CRUD, favoris, groupes, tags, import annuaire, fusion, tri) | 100% |
| F11 | Suivi d'acheminement | Partiel (MDN implémenté, pas de suivi complet envoyé/reçu/lu) | 50% |
| F12 | Délégation de traitement | Non implémenté | 0% |
| F13 | Analyse IA du contenu | **Implémenté** (chat IA, résumés, tags, recherche sémantique, actions IA, amélioration texte) | 100% |

**Couverture Phase 3 : 63%** (2/4 features implémentées, 1 partielle)

### Vue consolidée

| Phase | Horizon | Features | Impl. | Partiel | Non impl. | Couverture |
|---|---|---|---|---|---|---|
| **Phase 1 - Fondations** | T3 2026 | F1, F2, F6, F8, F10 | 2 | 2 | 1 | **60%** |
| **Phase 2 - Intelligence** | T4 2026 | F3, F4, F5, F7 | 3 | 0 | 1 | **75%** |
| **Phase 3 - Excellence** | T1-T2 2027 | F9, F11, F12, F13 | 2 | 1 | 1 | **63%** |
| **Global** | | **F1-F13** | **7** | **3** | **3** | **65%** |

### Effort restant par phase

| Phase | Features à compléter | Effort estimé |
|---|---|---|
| **Phase 1** | F1 (multi-boîtes IMAP simultané), F6 (intégration LGC), F10 (rôles/permissions) | **Élevé** - F10 nécessite un modèle RBAC complet |
| **Phase 2** | F7 (envoi Mon Espace Santé / DMP) | **Moyen** - intégration API DMP/MES avec homologation CNDA |
| **Phase 3** | F11 (suivi complet envoyé/reçu/lu), F12 (délégation) | **Moyen** - F12 nécessite un workflow de délégation avec notifications |

---

## 11. Synthèse par composant technique

### API Backend (Api/Mail)

Architecture Clean Architecture (.NET) : Domain, Application, Infrastructure, Api.

- Parsing CI-SIS/CDA complet
- Recherche sémantique hybride avec pgvector
- IA conversationnelle avec Semantic Kernel et plugins d'actions
- Service IMAP robuste avec sync background, mode online/offline
- Annuaire santé avec stratégies de recherche multiples
- Notifications temps réel dual SignalR + SSE
- Gestion des brouillons et actions en attente (mode offline)
- Embeddings dual Ollama/OpenAI
- **19 controllers API** : Mail, Contact, Directory, Search, AiChat, Ai, Biology, Connection, Draft, FeatureFlag, MailTemplate, Management, Notifications, Patients, Settings, Signature, Sync

### Client Blazor (Client/Blazor)

Architecture modulaire avec plugin system (IModule, IWidget, INotificationWidget, IAlertWidget).

- 70+ composants Razor (BiologyTimeline, ClinicalSynthesis, PatientTimeline, SearchMail, SearchPatient...)
- Widgets embarquables dans le shell HealthPlatform
- Chat IA intégré
- Gestion contacts avancée (merge, audit, import annuaire)
- Templates d'email avec placeholders

### Client Angular (Client/Angular/front)

Architecture Nx monorepo avec librairie `mss` (core, features, ui).

- 12 composants mail spécialisés (compose, detail, search, summary, tags, AI chat)
- Dashboard avec widgets (mail, biologie anormale, notifications, offline, sync)
- Gestion de contacts et groupes
- Service de notifications SSE réactif
- Recherche sémantique intégrée
- Brouillons avec sauvegarde automatique

---

## 12. Bibliothèque interop.cda.parser

Projet .NET dédié à l'interopérabilité CDA/IHE, composé de 3 assemblies complémentaires.

### 12.1 Architecture du projet

| Assembly | Rôle |
|----------|------|
| **Interop.Cda** | Cœur : entités CDA, builders de documents, helpers IHE, services de génération et validation |
| **Interop.Cda.Parser** | Parsing de documents CDA reçus : extraction des données cliniques, biologie, métadonnées, décompression XDM |
| **Interop.Cda.Converter** | Modèle de contenu CDA (`CdaContentModel`), résultats de biologie, adresses, conversion de données |

### 12.2 Construction de documents CDA (émission)

La chaîne de construction suit le pattern Builder avec les composants suivants :

| Classe | Responsabilité |
|--------|---------------|
| `CdaBuilder` | Construction du document clinique CDA complet (`POCD_MT000040ClinicalDocument`) : templates, identification, confidentialité, participants, corps |
| `CdaPatientBuilder` | Construction du bloc patient (`POCD_MT000040PatientRole`) : démographiques, INS-C, lieu de naissance, genre |
| `CdaMedicalRecordBuilder` | Construction du corps structuré (`StructuredBody`) : agrégation des sections médicales |
| `CdaComponentBuilder` | Fabrique de composants médicaux : pathologies, antécédents, allergies, points de vigilance, traitements chroniques, chirurgies |
| `CdaHtmlContentBuilder` | Génération du contenu HTML des sections CDA (tableaux de traitements, listes de points de vigilance) |

**Entités métier :**
- `CDADocument` : document CDA avec métadonnées (type, titre, visibilité, date, fichier, MIME)
- `CDAPatient` : patient avec INSC, adresse, téléphones, médecin traitant, volet médical
- `CDAAuteur` : auteur avec identifiant national, spécialité, structure, domaine
- `CDAVoletMedical` : volet médical structuré (pathologies, antécédents, facteurs de risque, points de vigilance, traitements chroniques, allergies, chirurgies)
- `CDAEntree` : entrée médicale avec code CIM, molécule, criticité, collatéral, mode de prescription

### 12.3 Génération de paquets IHE XDM (émission)

La génération de paquets IHE XDM conformes est assurée par une architecture en services :

| Classe | Responsabilité |
|--------|---------------|
| `IHEPackageBuilder` | API fluent pour configurer et générer un paquet IHE XDM (document, destination, logiciel, compression) |
| `IHEPackageGeneratorService` | Orchestrateur : création de l'arborescence IHE_XDM, génération CDA, README, INDEX, METADATA, compression ZIP |
| `MetadataGenerator` | Génération du fichier METADATA.XML conforme IHE : registre ebXML, auteur, patient, établissement, classifications |
| `IndexGenerator` | Génération du fichier INDEX.HTM |
| `ReadmeGenerator` | Génération du fichier README.TXT avec informations du logiciel émetteur |
| `PackageCompressionService` | Compression du paquet en archive ZIP |
| `CdaDataExtractor` | Extraction des données auteur, patient, legal authenticator, document depuis le CDA source |
| `FileMetadataService` | Calcul du hash et de la taille du fichier CDA pour le registre |

**Configuration :** `IHEPackageConfiguration` encapsule le document, le dossier de destination, les informations logiciel (`SoftwareInfo`), les chemins personnalisés (`PackagePaths`) et l'option de compression.

### 12.4 Parsing de documents CDA reçus (réception)

| Classe | Responsabilité |
|--------|---------------|
| `XDM` | Décompression et parcours d'archives IHE XDM reçues : extraction ZIP, détection des sous-dossiers IHE_XDM, lecture METADATA.XML |
| `SubmissionSet` | Parsing des métadonnées XDS (ExtrinsicObject, URI) et association avec les fichiers CDA contenus |
| `CdaFile` | Représentation d'un fichier CDA parsé : document XML, document clinique, modèle de contenu, résultats de biologie |
| `CdaParser` | Extraction complète des données d'un CDA : document, patient, biologie, laboratoire, prescripteur, métadonnées, documents liés |
| `CdaValidator` | Validation XSD du document CDA, déserialization, gestion des styles embarqués |

### 12.5 Transformation et export

| Classe | Responsabilité |
|--------|---------------|
| `CdaFormatTransformer` | Transformation CDA vers HTML (XSLT CI-SIS), vers Markdown (optimisé embeddings IA), vers texte depuis PDF |
| `CdaFileExporter` | Export CDA en fichier HTML autonome via feuille de style ASIP |

La transformation Markdown inclut un pipeline d'optimisation pour les embeddings : nettoyage HTML, transformation des tables 1-2 colonnes en listes, suppression des paragraphes orphelins, normalisation des headers.

### 12.6 Référentiels et codifications

| Classe | Responsabilité |
|--------|---------------|
| `OIDHelpers` | Constantes OID (INSC, CPS, GIP, HL7 Administrative Gender) et dictionnaire de systèmes de codes |
| `LOINCHelper` | Codes LOINC pour les sections CDA : pathologies, historique, antécédents, allergies, traitements |
| `TemplatesManager` | Dictionnaires de référence : relations patient (HL7 RoleCode), spécialités auteur (CI-SIS), types établissement, codes document, confidentialité |
| `CollateralConverters` | Conversion des liens de parenté patient vers codes HL7 (FTH, MTH, BRO, SIS, UNCLE, AUNT...) |
| `ConvertDocumentTypeConverter` | Conversion des types de documents CDA |

### 12.7 Biologie médicale

Le parsing des comptes-rendus de biologie exploite le modèle `CdaContentModel` :
- `LaboratoryResult` : résultats structurés avec parties de biologie (`BiologyParts`) et données non structurées
- `LaboratoryResultState` : interprétation selon HL7 ObservationInterpretation (N, L, H, A, LL, HH, AA)
- Détection automatique de l'état critique (CriticalLow, CriticalHigh, CriticalAbnormal) pour le déclenchement d'alertes

### 12.8 Impact sur la conformité

| Exigence Segur | Contribution de interop.cda.parser |
|---|---|
| MSS/va1.01 | Construction de paquets IHE_XDM pour la transmission de documents aux patients |
| MSS/va1.25 | Parsing CDA pour restitution des métadonnées dans la liste des messages |
| BIO/va1.01 | Détection des codes interprétation critiques (AA/HH/LL) via `LaboratoryResultState` |
| BIO/va1.05 | Extraction des éléments cliniques pertinents pour affichage dans la liste |
| BIO/va1.08 | Transformation CDA R2 N3 via feuille de style XSLT ASIP (`CdaFormatTransformer`, `CdaFileExporter`) |
| SC.CDA/VISU.01 | Rendu lisible des documents CDA via XSLT + export HTML |
| SC.CDA/INT.17 | Extraction des métadonnées de tri (type, date, auteur) depuis le CDA source |
| SC.MSS/CONF.14-15 | `CDADocument` fournit les données (INS, code CDA) nécessaires aux en-têtes X-MSS |

---

## 13. Score global spécification

| Catégorie | Implémenté | Partiel | Non implémenté |
|---|---|---|---|
| **Features (F1-F13)** | 7/13 (F2,F3,F4,F5,F8,F9,F13) | 3/13 (F1,F6,F11) | 3/13 (F7,F10,F12) |
| **JTBD** | 2/4 (JTBD1, JTBD4) | 2/4 (JTBD2, JTBD3) | - |
| **Contraintes techniques** | 4/7 | 2/7 | 1/7 |

**Score global : ~62% de la spécification couverte, avec les fondations techniques solides pour compléter les features manquantes.**

---
---

# PARTIE 2 - Conformité Ségur V1/V2 (périmètre MSSante uniquement)

**Source** : REM-MDV-LGC-Va2.xlsx - Onglet "Exigences REM vague 2"
**Périmètre retenu** : 72 exigences pertinentes pour le module messagerie (sur 198 totales, hors périmètre LGC Weda exclu)

## Résumé Ségur

| Statut | Nombre | % |
|--------|--------|---|
| **Implémenté** | 44 | 61% |
| Partiellement implémenté | 16 | 22% |
| Non implémenté | 12 | 17% |
| **Total périmètre messagerie** | **72** | **100%** |

---

## 1. Interopérabilité avec les opérateurs de MSSante

| ID | Vague | Exigence (résumé) | Statut | Référence code |
|----|-------|--------------------|--------|----------------|
| SC.MSS/CONF.01 | V2 | Connexion TLS 1.2 minimum avec API LPS | **Implémenté** | `ImapConnectionService.cs`, `SmtpConnectionFactory.cs` |
| SC.MSS/CONF.03 | V2 | Suites de chiffrement TLS autorisées | **Implémenté** | `TlsCipherSuiteValidator.cs` |
| SC.MSS/CONF.05 | V2 | SMTP conforme RFC 5321 avec STARTTLS | **Implémenté** | `SmtpConnectionFactory.cs` (MailKit) |
| SC.MSS/CONF.06 | V2 | IMAP4 conforme RFC 3501/9051 avec STARTTLS | **Implémenté** | `ImapConnectionService.cs`, `ImapClientWrapper.cs` |
| SC.MSS/CONF.07 | V2 | Cinématique connexion : TLS puis XOAUTH2 | **Implémenté** | STARTTLS + XOAUTH2 avec token PSC |
| SC.MSS/CONF.08 | V2 | Erreurs connexion ne perturbent pas les autres fonctions | **Implémenté** | Isolation via try/catch dans les services de connexion |
| SC.MSS/CONF.10 | V2 | Fin session quand Refresh Token PSC invalide | **Partiel** | `BackgroundSyncManager.cs` gère la déconnexion, détection expiration non explicite |
| SC.MSS/CONF.11 | V2 | Réouverture auto session si PSC encore valide | **Implémenté** | `ImapConnectionManager.cs` reconnexion automatique |
| SC.MSS/CONF.14 | V2 | En-tête SMTP X-MSS-INS dans messages avec IHE_XDM | **Non implémenté** | En-têtes X-MSS-* absentes du code d'envoi |
| SC.MSS/CONF.15 | V2 | En-tête SMTP X-MSS-CODECDA dans messages avec IHE_XDM | **Non implémenté** | |
| SC.MSS/CONF.16 | V2 | En-tête SMTP X-MSS-NIL dans tous les courriels | **Non implémenté** | |
| SC.MSS/CONF.22 | V2 | Conservation dernière CRL non expirée | **Implémenté** | `CrlValidationService.cs` |
| SC.MSS/CONF.27 | V2 | Certificat IGC Santé gamme Élémentaire Organisation uniquement | **Implémenté** | `CertificateValidator.cs` |
| SC.MSS/CONF.28 | V2 | Access Token PSC JWT non stocké de façon permanente | **Implémenté** | `UserContextInfo.cs` : tokens en mémoire de session |

---

## 2. Autoconfiguration de la BAL MSSante

| ID | Vague | Exigence (résumé) | Statut | Référence code |
|----|-------|--------------------|--------|----------------|
| SC.MSS/CONF.04 | V2 | Auto-configuration BAL via DNS SRV | **Implémenté** | `AutoconfigService.cs`, `AutodiscoveryHelper.cs` |

---

## 3. Envoi sécurisé vers Mon espace santé (patient)

| ID | Vague | Exigence (résumé) | Statut | Référence code |
|----|-------|--------------------|--------|----------------|
| SC.MSS/CONF.21 | V2 | En-tête X-MSS-MES "FIN" pour bloquer réponse patient | **Non implémenté** | |
| SC.MSS/UX.32 | V2 | Écrire à un usager depuis la base patients | **Partiel** | `SmtpService.cs` permet l'envoi ; sélection patient et vérification INS non implémentées |
| MSS/va1.01 | V1 | Transmettre documents Ségur aux patients via MSS (IHE_XDM) | **Partiel** | Envoi avec PJ possible, `IHEPackageBuilder` + `IHEPackageGeneratorService` génèrent les paquets IHE XDM complets ; intégration avec `SmtpService` pour l'envoi automatique non confirmée |
| MSS/va1.20 | V1 | Enregistrer opposition du patient à l'envoi MSS patient | **Non implémenté** | |
| MSS/va1.22 | V1 | Enregistrer opposition du patient à l'envoi MSS professionnel | **Non implémenté** | |

---

## 4. Intégration de l'annuaire santé

| ID | Vague | Exigence (résumé) | Statut | Référence code |
|----|-------|--------------------|--------|----------------|
| SC.MSS/CONF.20 | V2 | Recherche adresse MSSante dans Annuaire Santé | **Implémenté** | `AnnuaireSanteService.cs` + stratégies multiples |
| SC.MSS/UX.41 | V2 | Recherche multicritères : RPPS, nom, profession, spécialité, lieu | **Implémenté** | `RppsSearchStrategy.cs`, `NameSearchStrategy.cs`, `SpecialtySearchStrategy.cs`, `LocationSearchStrategy.cs`, `CombinedSearchStrategy.cs` |
| ANN/va1.01 | V1 | Intégrer Annuaire santé.fr (extraction publique ou API FHIR) | **Implémenté** | `AnnuaireSanteService.cs` via API FHIR |
| ANN/va1.02 | V1 | Intégrer données Annuaire pour les utilisateurs | **Implémenté** | `CreatePractitionerContactConsumer.cs` |
| ANN/va1.03 | V1 | Intégrer données Annuaire pour les correspondants | **Implémenté** | Stratégies de recherche + création contacts |
| ANN/va1.04 | V1 | Appels unitaires en temps réel via API FHIR | **Implémenté** | Appels temps réel dans les stratégies |

---

## 5. Intégration et gestion des documents reçus par MSSante

| ID | Vague | Exigence (résumé) | Statut | Référence code |
|----|-------|--------------------|--------|----------------|
| LGC.MSS/UX.05 | V2 | Gérer messages de suppression/modification de documents intégrés | **Non implémenté** | |
| SC.MSS/UX.25 | V2 | Distinguer messages professionnels vs patients (Mon espace santé) | **Partiel** | Adresse `@patient.mssante.fr` détectée, pas d'indicateur visuel explicite |
| SC.MSS/UX.28 | V2 | Masquer préfixe "XDM/1.0/DDM+" dans l'objet | **Non implémenté** | |
| SC.MSS/UX.31 | V2 | Afficher nom/prénom/INS de l'usager (pas juste l'email patient) | **Partiel** | Extraction patient via CDA, pas de résolution spécifique de l'adresse patient MSS |
| LGC.MDV.06 | V2 | Informer que le document a déjà été intégré | **Partiel** | `EnrichmentStatus` trace l'état, pas d'indicateur visuel "déjà intégré au dossier" |
| MSS/va1.25 | V1 | Restituer métadonnées CDA dans la liste messages reçus | **Implémenté** | `CdaParsingService.cs` : titre, type, date, patient, auteur, LOINC |
| MSS/va1.27 | V1 | Rattachement patient par comparaison visuelle si INS sans identité qualifiée | **Partiel** | `MailPatient.cs` stocke l'INS extrait, pas de workflow de rattachement visuel |
| MSS/va1.28 | V1 | Visualiser et classer en 1 clic dans le dossier patient | **Partiel** | Extraction auto des documents, classement "1 clic dossier patient" relève du LGC |
| ERGO/va1.05 | V1 | Liste messages : tri/filtre par date, patient, lu/non lu, type | **Implémenté** | Clients Blazor/Angular : tri date, filtre lu/non lu, recherche ; `MailRepository.cs` |
| ERGO/va1.08 | V1 | Liste messages reçus transversale depuis MSS | **Implémenté** | Dashboard MSS dans Blazor et Angular |

---

## 6. Envoi de messages et documents CDA par MSSante

| ID | Vague | Exigence (résumé) | Statut | Référence code |
|----|-------|--------------------|--------|----------------|
| MSS/va1.08 | V1 | En-têtes Message-ID, In-Reply-To, References conformes RFC 5322 | **Implémenté** | `EmailBuildingService.cs`, `SmtpService.cs` |
| MSS/va1.11 | V1 | Content-Type text/plain ou multipart/alternative | **Implémenté** | `EmailBuildingService.cs` |
| MSS/va1.12 | V1 | Message-ID conforme RFC 5322 | **Implémenté** | MailKit génère automatiquement |
| MSS/va1.13 | V1 | Pièce jointe respecte taille max (selon opérateur) | **Partiel** | Pas de vérification de taille avant envoi |
| MSS/va1.14 | V1 | Afficher bonne réception si accusé de réception | **Implémenté** | `MdnService.cs` |
| MSS/va1.15 | V1 | Permettre demande d'accusé DSN (Return-Receipt-To) | **Implémenté** | `SmtpService.cs`, `EmailAddressHelper.cs` |
| MSS/va1.16 | V1 | Libellé signifiant en complément de l'adresse expéditeur | **Partiel** | Display name extrait, formatage spécifique Titre_Prenom_NOM_Entite non implémenté |
| AMBU.MSS/va1.02 | V1 | Nouvelle version avec mention "annule et remplace" | **Non implémenté** |

---

## 7. Production et conservation de traces MSS

| ID | Vague | Exigence (résumé) | Statut | Référence code |
|----|-------|--------------------|--------|----------------|
| SC.MSS/CONF.17 | V2 | Traces fonctionnelles pour tous les traitements sur BAL | **Partiel** | Logging applicatif (`ILogger`) partout, pas de journal d'audit fonctionnel structuré |
| SC.MSS/CONF.18 | V2 | Chaque trace : identifiant auteur, horodatage, type action, demande serveur | **Partiel** | `RequestLoggingMiddleware.cs` trace les requêtes HTTP, pas toutes les actions IMAP/SMTP |
| SC.MSS/UX.37 | V2 | Tracer et historiser tous les flux de transmissions MSSante | **Partiel** | `PendingAction` historise les actions, pas de journal complet des transmissions |

---

## 8. Gestion des professionnels associés

| ID | Vague | Exigence (résumé) | Statut | Référence code |
|----|-------|--------------------|--------|----------------|
| LABEL.06 | V2 | Gérer la liste des professionnels associés à la prise en charge | **Partiel** | `Contact.cs` gère les contacts/groupes, pas de lien formel "professionnels du patient" |

---

## 9. Biologie médicale (reçue par MSSante)

| ID | Vague | Exigence (résumé) | Statut | Référence code |
|----|-------|--------------------|--------|----------------|
| LGC.MDV.08 | V2 | Intégrer CR de biologie conformément au CI-SIS | **Implémenté** | `CdaParsingService.cs`, `MailMedicalDocumentBiology` |
| LGC.MDV.09 | V2 | Exploiter jeu de valeurs Circuit de la biologie, conversion unités | **Non implémenté** | Pas de conversion d'unités ni comparaison entre CR-BIO |
| BIO/va1.01 | V1 | Alerte spécifique si code interprétation AA/HH/LL (critique) | **Implémenté** | `BiologyService.GetPatientsWithAbnormalUnreadResultsAsync`, `NewMailNotifier.HandleAbnormalBiologyAsync` |
| BIO/va1.05 | V1 | Élément clinique pertinent visible dans la liste messages | **Implémenté** | `HasBiologyResults` flag, dashboard "Résultats anormaux" |
| BIO/va1.06 | V1 | Signaler résultats en écart par rapport à l'intervalle de référence | **Partiel** | Détection résultats anormaux, pas de comparaison fine avec intervalle fourni |
| BIO/va1.08 | V1 | Afficher CR biologie CDA R2 N3 avec feuille de style | **Implémenté** | `CdaFormatTransformer.TransformToHtml` via feuille de style XSLT ASIP, `CdaFileExporter.TransformToHtmlFile` |

---

## 10. Affichage des documents CDA reçus

| ID | Vague | Exigence (résumé) | Statut | Référence code |
|----|-------|--------------------|--------|----------------|
| SC.CDA/DD.15 | V2 | Une seule ligne pour CDA R2 N3 avec PDF encapsulé | **Partiel** | `MailMedicalDocument` unitaire, pas de fusion explicite N3+PDF à l'affichage |
| SC.CDA/VISU.03 | V2 | Afficher préférentiellement le PDF encapsulé | **Partiel** | Extraction CDA, pas de logique de priorité PDF vs narrative |
| SC.CDA/VISU.01 | V2 | Rendre lisible un CDA (en-tête, corps N1, parties narratives N3) | **Implémenté** | `CdaFormatTransformer.TransformToHtml` avec XSLT ASIP, gestion des styles embarqués (`EmbeddedStyleHelper`) |
| SC.CDA/INT.18 | V2 | Vérifier cohérence de tout document CDA reçu (détection doublons) | **Partiel** | `IheXdmProcessingService.cs` traite les documents, pas de détection explicite de doublons |

---

## 11. Navigation dans le dossier patient (documents reçus par MSS)

| ID | Vague | Exigence (résumé) | Statut | Référence code |
|----|-------|--------------------|--------|----------------|
| SC.CDA/INT.04 | V2 | Trier documents importés par type et date | **Implémenté** | `PatientService.cs`, tri dans les clients |
| SC.CDA/INT.08 | V2 | Identifier visuellement l'origine (DMP / MSSante) | **Implémenté** | `MailMedicalDocument` lié au `Mail` d'origine |
| SC.CDA/INT.17 | V2 | Informations de tri par défaut issues du CDA | **Implémenté** | Métadonnées CDA extraites par `CdaParsingService.cs` |
| LGC.DMP/UX.10 | V2 | Système fonctionnel sans bloquer l'interface | **Implémenté** | Architecture asynchrone, background sync, SignalR/SSE |

---

## 12. Authentification PSC (périmètre messagerie)

| ID | Vague | Exigence (résumé) | Statut | Référence code |
|----|-------|--------------------|--------|----------------|
| SC.PSC.01 | V2 | Configurer PSC comme fournisseur d'identité | **Implémenté** | `UserContextInfo.cs` : tokens PSC/Keycloak, `RequestHelper.cs` |

---

## 13. Sécurité (périmètre messagerie)

| ID | Vague | Exigence (résumé) | Statut | Référence code |
|----|-------|--------------------|--------|----------------|
| SC.SSI/IE.33 | V2 | Gérer identifiants professionnel (RPPS, nom, prénom, profession) | **Implémenté** | `UserContextInfo.cs`, `Contact.cs` |
| SC.SSI/IE.38 | V2 | Permettre au professionnel de fermer sa session | **Partiel** | Tokens en mémoire de session, pas de bouton de déconnexion explicite confirmé |
| SC.SSI/IE.58 | V2 | Verrouillage après 2h d'inactivité | **Non implémenté** | |

---

## 14. Identité patient (périmètre messagerie : réception documents)

| ID | Vague | Exigence (résumé) | Statut | Référence code |
|----|-------|--------------------|--------|----------------|
| SENTINELLE.20 | V2 | Recherche identité connue à réception d'un document avec INS qualifiée | **Partiel** | `MailPatient.cs` stocke l'INS, `PatientService.GetByInsAsync` recherche par INS. Logique complète de rapprochement dans le LGC |
| INS/va1.53 | V1 | Ne pas transmettre INS si identité non qualifiée | **Partiel** | `MailPatient.cs` stocke l'INS, logique de non-transmission dans le LGC |

---

# SYNTHÈSE GLOBALE

## Score spécification fonctionnelle

| Catégorie | Implémenté | Partiel | Non implémenté |
|---|---|---|---|
| Features (F1-F13) | **7**/13 | 3/13 | 3/13 |
| JTBD (1-4) | **2**/4 | 2/4 | 0/4 |

**Couverture spécification : ~62%**

## Score Ségur (périmètre MSSante)

| Statut | Nombre | % |
|--------|--------|---|
| **Implémenté** | **44** | 61% |
| Partiellement implémenté | 16 | 22% |
| Non implémenté | 12 | 17% |

**Couverture Ségur MSS : 61% implémenté, 83% au moins partiellement couvert**

## Points forts

- Connexion IMAP/SMTP sécurisée (TLS 1.2+, cipher suites validées, certificats IGC Santé, CRL/OCSP)
- Auto-configuration BAL via DNS SRV
- Annuaire Santé intégré via API FHIR avec recherche multicritères
- Parsing CDA R2 / IHE_XDM complet avec extraction métadonnées CI-SIS (`interop.cda.parser`)
- Construction de documents CDA et génération de paquets IHE XDM conformes (builders + `IHEPackageGeneratorService`)
- Rendu CDA via feuille de style XSLT ASIP (`CdaFormatTransformer`) + conversion Markdown pour embeddings IA
- Référentiels intégrés : OID, LOINC, HL7 RoleCode, spécialités CI-SIS, types établissement
- En-têtes RFC 5322 (Message-ID, In-Reply-To, References)
- Accusés de réception (MDN / DSN)
- Détection et alerte des résultats de biologie anormaux
- Architecture asynchrone non bloquante (SignalR, SSE, background sync)
- IA conversationnelle, résumés, tags, recherche sémantique

## Actions prioritaires pour compléter la conformité Ségur

1. **En-têtes SMTP MSSante** : implémenter X-MSS-INS, X-MSS-CODECDA, X-MSS-NIL, X-MSS-MES dans `SmtpService.cs`
2. **Masquage préfixe XDM** : filtrer "XDM/1.0/DDM+" dans l'objet des messages reçus
3. **Opposition patient** : ajouter la gestion de l'opposition à l'envoi MSS patient/professionnel
4. **Traces MSS** : implémenter un journal d'audit fonctionnel structuré (identifiant auteur, horodatage, type action)
5. **Distinction pro/patient** : indicateur visuel dans la liste des messages reçus
6. **Annule et remplace** : mécanisme de renvoi avec mention pré-paramétrée
7. **Conversion unités biologie** : exploiter le jeu de valeurs Circuit de la biologie pour la comparaison inter-CR
8. **Verrouillage session** : auto-lock après inactivité configurable

## Cartographie des fichiers sources clés

| Composant | Fichiers | Exigences couvertes |
|-----------|----------|---------------------|
| Connexion IMAP | `ImapConnectionService.cs`, `ImapConnectionManager.cs`, `ImapClientWrapper.cs` | SC.MSS/CONF.01-.11 |
| Connexion SMTP | `SmtpConnectionFactory.cs`, `SmtpService.cs` | SC.MSS/CONF.05, .07, .14-.16 |
| Sécurité TLS | `TlsCipherSuiteValidator.cs`, `CertificateValidator.cs` | SC.MSS/CONF.03, .27 |
| Révocation certificats | `CrlValidationService.cs`, `OcspValidationService.cs` | SC.MSS/CONF.22 |
| Auto-configuration | `AutoconfigService.cs`, `AutodiscoveryHelper.cs` | SC.MSS/CONF.04 |
| Annuaire Santé | `AnnuaireSanteService.cs`, `Strategies/*.cs` | SC.MSS/CONF.20, UX.41, ANN/va1.* |
| Parsing CDA/XDM | `CdaParsingService.cs`, `IheXdmProcessingService.cs`, `interop.cda.parser` (CdaParser, XDM, SubmissionSet) | MSS/va1.25, .27, .28 |
| Construction CDA/IHE | `CdaBuilder`, `IHEPackageBuilder`, `IHEPackageGeneratorService`, `MetadataGenerator` | MSS/va1.01 |
| Rendu CDA | `CdaFormatTransformer`, `CdaFileExporter` | BIO/va1.08, SC.CDA/VISU.01 |
| Référentiels CDA | `OIDHelpers`, `LOINCHelper`, `TemplatesManager`, `CollateralConverters` | Conformité CI-SIS |
| Construction emails | `EmailBuildingService.cs`, `EmailAddressHelper.cs` | MSS/va1.08, .11, .12, .15 |
| Biologie | `BiologyService.cs`, `MailMedicalDocumentBiology`, `LaboratoryResult`, `LaboratoryResultState` | BIO/va1.01, .05, .06, .08 |
| Notifications | `NewMailNotifier.cs`, `MailHub.cs`, `SseNotificationBroker` | Alertes biologie anormale |
| MDN | `MdnService.cs` | MSS/va1.14 |
| Drafts / Envoi | `DraftService.cs`, `SmtpService.cs` | Envoi MSSante |
| Sync background | `BackgroundSyncService.cs`, `BackgroundImapService.cs` | Synchronisation continue |
| Actions en attente | `PendingActionService.cs`, `PendingAction.cs` | Mode hors ligne |
| Contexte utilisateur | `UserContextInfo.cs` | PSC tokens, RPPS |
| IA / Semantic | `SemanticSearchService.cs`, `EmailActionsPlugin.cs` | Priorisation intelligente |
