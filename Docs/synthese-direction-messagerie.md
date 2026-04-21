# Module Messagerie MSSante - Synthèse Direction Produit

**Date** : 11/04/2026
**Objet** : État d'avancement et niveau de couverture du module Messagerie Sécurisée de Santé (MSSante)

---

## Vue d'ensemble

Le module Messagerie MSSante de HealthPlatform (POC développé par Pascal Cabanel hors WEDA) est un client de messagerie sécurisée destiné aux professionnels de santé, conforme aux exigences du Ségur du numérique. Il permet de recevoir, traiter, classer et envoyer des documents médicaux via le réseau MSSante, avec une couche d'intelligence artificielle pour assister le praticien au quotidien.

---

## Indicateurs clés de couverture

### Spécification fonctionnelle

| | Couvert | En cours | À faire |
|---|---|---|---|
| **Fonctionnalités (13)** | **7** (54%) | 3 (23%) | 3 (23%) |
| **Cas d'usage métier (4)** | **2** (50%) | 2 (50%) | 0 |

**Couverture globale de la spécification : 65%**

### Conformité Ségur V1/V2 (périmètre MSSante - 72 exigences)

| | Nombre | % |
|---|---|---|
| **Conforme** | **44** | **61%** |
| Partiellement conforme | 16 | 22% |
| Non conforme | 12 | 17% |

**83% des exigences Ségur sont au moins partiellement couvertes.**

---

## Ce qui fonctionne aujourd'hui

### Réception et traitement des documents médicaux

- Les documents médicaux reçus par MSSante (comptes-rendus, biologie, courriers...) sont **automatiquement analysés et classés** : identification du patient (INS), du praticien auteur, du type de document et des métadonnées médicales
- Les **résultats de biologie anormaux ou critiques** sont détectés automatiquement et remontent en **alerte prioritaire** dans le tableau de bord
- Les documents CDA sont **rendus lisibles** via une feuille de style officielle (CI-SIS/ASIP), aussi bien en HTML qu'en format texte pour l'indexation
- Le praticien dispose d'un **tableau de bord synthétique** : résumé du jour, résultats anormaux, notifications

### Envoi de messages et documents

- Composition de messages avec pièces jointes, brouillons, accusés de réception
- **Annuaire Santé intégré** : recherche de correspondants par RPPS, nom, spécialité, localisation, établissement
- Carnet d'adresses personnel avec favoris, groupes et historique d'utilisation
- Les en-têtes techniques des messages sont conformes aux standards (RFC 5322)

### Interopérabilité et standards

- **Connexion sécurisée** aux opérateurs MSSante : TLS 1.2+, validation des certificats, authentification Pro Santé Connect (PSC)
- **Auto-configuration** de la boîte aux lettres MSSante (découverte automatique des serveurs)
- **Lecture et génération de paquets IHE XDM** conformes au cadre d'interopérabilité des systèmes d'information de santé (CI-SIS)
- Référentiels médicaux intégrés : LOINC, OID, nomenclatures HL7, spécialités CI-SIS

### Intelligence artificielle

- **Résumés automatiques** des messages et documents reçus
- **Suggestions de tags** et priorisation par IA
- **Chat conversationnel** pour interroger sa messagerie en langage naturel
- **Recherche sémantique** (au-delà de la simple recherche par mots-clés)
- Fonctionne en mode on-premise (données qui restent dans l'établissement) ou cloud, au choix

### Expérience utilisateur

- Deux clients disponibles : un module embarquable dans HealthPlatform (Blazor) et une application web autonome (Angular)
- Widgets intégrés au tableau de bord principal : nouveaux messages, alertes biologie, notifications
- Vue patient dédiée avec historique des documents reçus par MSSante
- Mode hors ligne avec synchronisation automatique au retour de la connexion

---

## Couverture par profil utilisateur

| Profil | Couverture | Commentaire |
|---|---|---|
| **Médecin** | Bonne | Tableau de bord, alertes biologie, IA, vue patient, recherche sémantique |
| **Secrétaire médicale** | Partielle | Contacts, annuaire, tags. Manque une vue organisationnelle et un workflow de pré-classement |
| **Coordinateur de soins** | Partielle | Historique patient, recherche avancée. Manque un tableau de bord de coordination |
| **Patient (Mon Espace Santé)** | Non couverte | Pas d'intégration Mon Espace Santé / DMP |

---

## Avancement par jalon

### Phase 1 - Fondations (horizon T3 2026) - Couverture 60%

| Fonctionnalité | État |
|---|---|
| Classement automatique des documents (INS, CI-SIS) | **Disponible** |
| Annuaire Santé intégré (RPPS, MSSante) | **Disponible** |
| Boîte de réception (mono-boîte) | **Disponible** (multi-boîtes à finaliser) |
| Envoi contextuel depuis le dossier patient | **En cours** (composition disponible, lien LGC à finaliser) |
| Gestion des rôles et permissions (boîtes organisationnelles) | À faire |

### Phase 2 - Intelligence (horizon T4 2026) - Couverture 75%

| Fonctionnalité | État |
|---|---|
| Priorisation intelligente (sévérité, IA) | **Disponible** |
| Widget documents dans le dossier patient | **Disponible** |
| Alertes temps réel (biologie anormale, urgences) | **Disponible** |
| Envoi vers Mon Espace Santé (DMP/MES) | À faire |

### Phase 3 - Excellence (horizon T1-T2 2027) - Couverture 63%

| Fonctionnalité | État |
|---|---|
| Carnet d'adresses (favoris, groupes, import) | **Disponible** |
| Analyse IA du contenu (résumés, tags, chat, recherche sémantique) | **Disponible** |
| Suivi d'acheminement des messages | **En cours** (accusés de réception disponibles, suivi complet à finaliser) |
| Délégation de traitement entre professionnels | À faire |

### Vue consolidée

| Phase | Horizon | Couverture |
|---|---|---|
| **Fondations** | T3 2026 | **60%** |
| **Intelligence** | T4 2026 | **75%** |
| **Excellence** | T1-T2 2027 | **63%** |

---

## Conformité Ségur par domaine

| Domaine | Exigences | Conformes | Partielles | Non conformes |
|---|---|---|---|---|
| Connexion et sécurité MSSante | 14 | 10 | 1 | 3 |
| Auto-configuration BAL | 1 | 1 | 0 | 0 |
| Envoi vers patients (Mon Espace Santé) | 5 | 0 | 2 | 3 |
| Annuaire Santé | 6 | 6 | 0 | 0 |
| Documents reçus par MSSante | 10 | 3 | 5 | 2 |
| Envoi de messages et documents | 7 | 5 | 1 | 1 |
| Traces et audit | 3 | 0 | 3 | 0 |
| Professionnels associés | 1 | 0 | 1 | 0 |
| Biologie médicale | 6 | 4 | 1 | 1 |
| Affichage documents CDA | 4 | 1 | 3 | 0 |
| Navigation dossier patient | 4 | 4 | 0 | 0 |
| Authentification PSC | 1 | 1 | 0 | 0 |
| Sécurité | 3 | 1 | 1 | 1 |
| Identité patient (INS) | 2 | 0 | 2 | 0 |

**Points de force Ségur :** annuaire santé (100%), auto-configuration (100%), navigation dossier patient (100%), authentification PSC (100%), biologie médicale (67% conforme).

**Points d'attention Ségur :** envoi vers patients (0% conforme), traces et audit (0% conforme), sécurité session (33% conforme).

---

## Actions prioritaires pour atteindre la conformité

Les actions ci-dessous sont classées par impact sur la conformité Ségur et le parcours utilisateur.

### Priorité haute

| Action | Impact | Effort |
|---|---|---|
| **En-têtes SMTP MSSante** (X-MSS-INS, X-MSS-CODECDA, X-MSS-NIL, X-MSS-MES) | 4 exigences Ségur V2 non conformes | Faible |
| **Opposition patient** à l'envoi MSS | 2 exigences Ségur V1 non conformes | Faible |
| **Journal d'audit** des actions MSSante | 3 exigences Ségur V2 partielles | Moyen |
| **Masquage du préfixe XDM** dans l'objet des messages | 1 exigence Ségur V2 + confort utilisateur | Faible |

### Priorité moyenne

| Action | Impact | Effort |
|---|---|---|
| **Envoi vers Mon Espace Santé** (DMP/MES) | 1 feature majeure + homologation CNDA | Élevé |
| **Gestion multi-boîtes** (boîtes organisationnelles) | 1 feature + cas d'usage secrétaire/coordinateur | Élevé |
| **Distinction visuelle** messages pro / patient dans la liste | 1 exigence Ségur V2 + lisibilité | Faible |
| **Mention "annule et remplace"** pour les renvois de documents | 1 exigence Ségur V1 | Faible |

### Priorité basse

| Action | Impact | Effort |
|---|---|---|
| **Verrouillage automatique** après inactivité | 1 exigence sécurité Ségur V2 | Faible |
| **Suivi d'acheminement complet** (envoyé / reçu / lu) | Amélioration du suivi au-delà des accusés | Moyen |
| **Délégation de traitement** entre professionnels | Feature d'excellence, scénarios avancés | Élevé |
| **Conversion d'unités biologie** et comparaison inter-CR | 1 exigence Ségur V2, scénarios avancés | Moyen |

---

## Risques identifiés

| Risque | Mitigation en place |
|---|---|
| Classement automatique insuffisant sur certains documents | Mécanisme de retry, assistance IA, retour au classement manuel possible |
| Latence de l'annuaire national de santé | Stratégies de recherche optimisées, cache |
| Résistance au changement des utilisateurs | Mode hors ligne, personnalisation de l'interface, activation progressive des fonctionnalités |
| Contraintes de confidentialité sur les données de santé avec l'IA | Mode on-premise disponible (données restent dans l'établissement), désactivation IA possible |
| Évolution des référentiels MSSante | Architecture modulaire facilitant les mises à jour |

---

## En résumé

Le module Messagerie MSSante couvre aujourd'hui **les fondations essentielles** : réception et classement automatique des documents, connexion sécurisée, annuaire intégré, alertes biologie et assistance IA. La couverture Ségur atteint **83% au moins partiellement**, avec **61% de conformité complète**.

Les principaux chantiers restants pour une conformité Ségur complète portent sur :
- Les **en-têtes SMTP spécifiques** MSSante (impact faible, effort faible)
- La **traçabilité** des actions (effort moyen)
- L'**envoi vers Mon Espace Santé** (effort élevé, nécessite homologation)
- La **gestion multi-boîtes organisationnelles** (effort élevé)

Le socle technique et fonctionnel est solide et permet d'envisager la finalisation de la conformité de manière progressive sur les jalons prévus.
