# E012 — Client mobile MSSanté

> **Statut** : 🟢 En cours
> **Modèle** : task-driven
> **Version** : 1.0
> **Auteur** : PO forge
> **Audience** : PO, médecin, direction — la vue ingénierie vit dans [E012-Changelogs.md](E012-Changelogs.md)
> **Dernière mise à jour** : 2026-06-29 (task-136)

---

<!-- toc:start — section générée par /tech-writer ; ne pas éditer manuellement -->

## Sommaire

- [1. Vision](#1-vision)
- [2. Objectifs métier](#2-objectifs-métier)
- [3. Acteurs concernés](#3-acteurs-concernés)
- [4. Features de l'EPIC](#4-features-de-lepic)
- [5. Workflow entre Features](#5-workflow-entre-features)
- [6. Règles métier transverses](#6-règles-métier-transverses)
- [7. Contraintes et hypothèses](#7-contraintes-et-hypothèses)
- [8. Critères d'acceptation de l'EPIC](#8-critères-dacceptation-de-lepic)
- [9. Hors périmètre (ce batch)](#9-hors-périmètre-ce-batch)
- [État de couverture (2026-06-29)](#état-de-couverture-2026-06-29)
- [Synthèse fonctionnelle des changelogs](#synthèse-fonctionnelle-des-changelogs)

<!-- toc:end -->

## 1. Vision

Offrir au médecin une **version mobile de la messagerie sécurisée santé**
(Ionic + Angular + Capacitor) qui ne perde **aucune fonctionnalité d'affichage**
par rapport au client web `client-angular` : mêmes titres, même identité
patient, mêmes alertes, même contenu HTML, mêmes pièces jointes, même biologie.
Le client mobile est construit en **miroir structurel** du client Angular —
mêmes noms de composants, même découpage — pour fluidifier la maintenance et le
travail assisté par IA.

## 2. Objectifs métier

- [ ] Consulter ses emails MSSanté sur mobile avec un contenu **identique** au web
- [ ] Naviguer entre les répertoires de la boîte
- [ ] Gérer ses messages : lu/non-lu, supprimer, déplacer
- [ ] Envoyer, répondre, transférer un email MSSanté
- [ ] Voir et acquitter les résultats de **biologie** anormale
- [ ] Conserver la parité d'architecture avec `client-angular`

## 3. Acteurs concernés

| Acteur | Rôle dans l'EPIC |
|--------|------------------|
| Médecin généraliste | Utilisateur principal — lit, gère et envoie ses messages en mobilité |
| Patient | Émetteur/destinataire de messages (identité affichée, jamais en clair dans logs/URL) |
| Laboratoire / confrère | Émetteur de documents médicaux et de résultats de biologie |

## 4. Features de l'EPIC

| Task | Feature | Composants miroir | Statut |
|------|---------|-------------------|--------|
| task-095 | Socle `features/mail` + parité Inbox + sélection de répertoire | `mail-list`, `mail-header`, `mail-folder-list`, `mail-folder-item` | ✅ mergée |
| task-096 | Parité consultation email | `mail-detail`, `mail-body`, `medical-html-frame` | ✅ mergée |
| task-097 | Pièces jointes | `mail-attachment` | ✅ mergée |
| task-098 | Biologie : affichage + acquittement | `biology`, `biology-ack-panel`, `biology-ack-confirm-dialog`, `biology-ack-badge`, `inbox-biology-ack-chip` | ✅ mergée |
| task-099 | Actions message : lu/non-lu, flag, supprimer, déplacer | actions `mail-list`/`mail-header`/`mail-detail` + `mail-actions.service` | ✅ mergée |
| task-100 | Compose / envoi (nouveau, répondre, transférer, Cc/Cci, accusé) | `mail-compose`, `html-editor` | ✅ mergée |
| task-101 | HTML CDA responsive mobile (interop-cda) | `cda_asip.xsl` (CSS embarqué) | ✅ mergée |
| task-102 | Refresh de session JWT (refresh + replay) | `MssHeadersInterceptor`, `AuthService` | ✅ mergée |
| task-103 | Pagination inbox orientée scroll (infinite scroll) | `mail-state`, `inbox.page` | ✅ mergée |
| task-104 | Enrichissement + mises à jour live SSE | `mss-api`, `mail-events-stream`, `inbox`/`mail-detail` | ✅ mergée |
| task-105 | Accusé de lecture — réponse (sur consentement) | `mss-api`, `mail-detail` | ✅ mergée |
| task-106 | Recherche d'emails | `mail-search`, `mss-api`, `mail-state` | ✅ mergée |
| task-107 | Notifications nouveaux mails (SSE in-app) | `notification-stream`, `inbox` | ✅ mergée |
| task-108 | Vue Conversations (threads) | `mss-api`, `mail-state`, `mail-header`, `mail-list` | ✅ mergée |
| task-131 | Synthèse IA d'un email (panneau dans le détail) | `mail-summary` | ✅ mergée |
| task-132 | Vue patient — socle : recherche + fiche + opposition | `mss-patient`, `patient-search`, `patient-card`, `patient-consent` | ✅ mergée |
| task-133 | Vue patient — timeline documents médicaux + viewer | `mss-patient-timeline`, `mss-timeline-document-group`, `mss-timeline-period-separator`, `mss-medical-document-modal` | ✅ mergée |
| task-134 | Vue patient — timeline biologie matricielle | `mss-biology-timeline` | ✅ mergée |
| task-135 | Vue patient — synthèse clinique & antécédents | `mss-clinical-synthesis`, `mss-medical-history` | ✅ mergée |
| task-136 | Connexion CIBA e-CPS (RPPS + validation découplée) | `login.page`, `auth.service`, `ciba.util` | 🟡 PR ouverte |

> Le bilan d'avancement par feature (statut, couverture, tasks contributives)
> est consigné en fin de document, dans la section *État de couverture*.

## 5. Workflow entre Features

```
task-095 (socle + inbox + dossiers)
   └─→ task-096 (consultation)
          ├─→ task-097 (pièces jointes)
          ├─→ task-098 (biologie + acquittement)
          ├─→ task-099 (actions message)
          └─→ task-100 (compose / envoi)

task-132 (vue patient — socle : recherche + fiche + opposition)
   └─→ task-133 (timeline documents médicaux + viewer)
          ├─→ task-134 (timeline biologie matricielle)
          └─→ task-135 (synthèse clinique & antécédents)

task-136 (connexion CIBA e-CPS — socle d'authentification mobile, indépendant)
```

## 6. Règles métier transverses

- **Parité structurelle** : mêmes noms de composants/services et même
  découpage que `client-angular` (lib `front/libs/mss`).
- **Aucune perte d'affichage** : tout ce que le web montre (titre du document
  médical, identité patient, badges/alertes, HTML, PJ, biologie) doit être
  visible sur mobile.
- **Libellés FR en dur** (pas de ngx-translate — convention MSS).
- **Authentification PS** : PSC / e-CPS (déjà en place sur mobile).
- **Aucune donnée de santé en clair** (INS, NIR, contenu CDA, contenu MSSanté)
  dans les logs, les libellés, les URL ou les sujets.

## 7. Contraintes et hypothèses

- Backend `api-mail` **inchangé** : le mobile consomme les endpoints existants
  (déjà consommés par `client-angular`). Aucun changement de contrat.
- `client-mobile` est un repo **full-automation** (GitHub, branche `develop`) :
  la forge code, commit, push, ouvre la PR et lance `/lint-mobile`.
- Les types DTO mobiles sont des **transpositions TS** régénérées manuellement
  (pas de NuGet).

## 8. Critères d'acceptation de l'EPIC

- [ ] Le médecin retrouve sur mobile **le même contenu** que sur le web pour un
  email donné (comparaison côte à côte).
- [ ] Répertoires, consultation, lu/non-lu, suppression, envoi fonctionnels.
- [ ] Biologie visible + acquittable.
- [ ] Build + tests verts à chaque task ; lint propre.

## 9. Hors périmètre (ce batch)

Rattachement patient, dédoublonnage, IA (tags/résumé/chat), recherche,
conversations/threads, drag-drop, signatures, templates, éditeur HTML riche,
brouillons auto-sauvegardés.

---

## État de couverture (2026-06-29)

- **Batch initial (task-095 → task-100)** : 6/6 mergées sur `develop` (PR #1 → #6).
  Client mobile fonctionnel : consultation à parité, répertoires, pièces jointes,
  biologie + acquittement, actions (lu/non-lu, flag, suppr, déplacer), compose/envoi.
- **task-101** (interop-cda) : mergée — HTML CDA responsive mobile. Suivi : bump
  consommateur `api-mail` (NuGet) après publication pour effet end-to-end.
- **task-102** : mergée — refresh de session JWT (refresh + rejeu + redirection login).
- **task-103** : mergée — pagination inbox orientée scroll (infinite scroll).
- **task-104** : mergée — enrichissement + mises à jour live SSE (liste + détail).
- **task-105** : mergée — accusé de lecture en réponse (sur consentement PS).
- **task-106** : mergée — recherche d'emails.
- **task-107** : mergée — notifications nouveaux mails (SSE in-app ; push native = suivi infra).
- **task-108** : mergée — vue Conversations (threads). Clôt le batch issu de l'analyse différentielle. **Tout E012 (095→108) est mergé sur `develop`.**
- **task-131** : mergée — synthèse IA d'un email dans le détail (parité du
  panneau « Synthèse IA » du client web).
- **task-132** : mergée — **socle de la vue patient** : l'onglet Patients
  devient fonctionnel (recherche d'un patient, fiche démographique, gestion
  de l'opposition MSSanté).
- **task-133** : mergée — **timeline des documents médicaux** du patient :
  liste paginée groupée par période, filtres par type, et visionneuse
  (PDF + vues structurées).
- **task-134** : mergée — **timeline biologie matricielle** : onglet Biologie
  (biomarqueurs × dates) avec tendances, sparklines, filtre anormaux et
  sélecteur de période.
- **task-135** : mergée — **synthèse clinique & antécédents** : onglet Synthèse
  (allergies critiques, problèmes actifs, traitements, vaccinations, mode de vie,
  antécédents) en cartes empilées + sections d'antécédents repliables. **Clôt le
  portage de la vue patient mobile (4/4).**
- **task-136** : PR ouverte (en attente de merge humain) — **connexion CIBA
  e-CPS** : la connexion par e-CPS (saisie du RPPS + validation découplée sur
  l'application e-CPS du praticien, avec code de vérification à 2 chiffres)
  devient le **moyen principal** d'authentification sur mobile ; la redirection
  Pro Santé Connect web passe en **moyen secondaire**. Le dernier RPPS utilisé
  est pré-rempli à la connexion suivante.

## Synthèse fonctionnelle des changelogs

- **v1.19 (task-136)** — Connexion e-CPS : la **connexion par e-CPS** devient le
  moyen principal d'accès à la messagerie mobile. Le praticien saisit son **RPPS**
  (pré-rempli s'il s'est déjà connecté), valide, et l'application affiche un
  **code à 2 chiffres** à comparer avec celui présenté par son application e-CPS
  avant de valider la demande (protection anti-hameçonnage). La validation se
  fait **sans quitter l'application** ; la connexion Pro Santé Connect par
  navigateur reste disponible en second choix (« Autre moyen de connexion »).
  En cas de demande non validée à temps, de RPPS inconnu ou de service
  indisponible, un message clair en français guide le praticien. Détail :
  [E012-Changelogs.md](E012-Changelogs.md).
- **v1.18 (task-135)** — Vue patient (synthèse clinique) : un onglet **Synthèse**
  s'ajoute à la fiche du patient (quand des éléments de synthèse existent). Le
  médecin dispose d'une **synthèse clinique consolidée** : bannière des allergies
  critiques en tête, puis des cartes par catégorie (allergies, problèmes actifs,
  traitements avec posologie, antécédents, vaccinations, mode de vie, antécédents
  familiaux), colorées selon la gravité. En dessous, le **détail des antécédents**
  s'ouvre en sections repliables (une à la fois). La même synthèse structurée
  s'affiche aussi à l'ouverture d'un document de synthèse depuis la timeline.
  Avec cette livraison, la **vue patient mobile est complète (4/4)**. Détail :
  [E012-Changelogs.md](E012-Changelogs.md).
- **v1.17 (task-134)** — Vue patient (biologie) : un onglet **Biologie**
  s'ajoute à la fiche du patient (quand des résultats existent). Le médecin
  visualise l'**évolution des biomarqueurs dans le temps** sous forme de
  tableau (analyses en lignes, dates en colonnes), avec valeurs colorées selon
  l'interprétation, indicateur de tendance, mini-courbe par biomarqueur, filtre
  par nom, bascule « anormaux uniquement » et sélection de période (3/6/12 mois
  ou tout). Détail : [E012-Changelogs.md](E012-Changelogs.md).
- **v1.16 (task-133)** — Vue patient (documents) : depuis la fiche d'un patient,
  le médecin parcourt tous ses **documents médicaux**, regroupés par période
  (Aujourd'hui, Cette semaine, Ce mois…) et filtrables par type (biologie,
  imagerie, comptes-rendus…). Il ouvre un document en plein écran : le PDF
  d'origine quand il existe (avec téléchargement), sinon le contenu mis en
  forme. Le défilement charge automatiquement les documents plus anciens.
  Détail : [E012-Changelogs.md](E012-Changelogs.md).
- **v1.15 (task-132)** — Vue patient (socle) : l'onglet « Patients » devient
  fonctionnel. Le médecin recherche un patient (par nom, ou retrouve d'emblée
  les patients ayant reçu des documents le jour même), ouvre sa fiche
  (identité, âge, sexe, INS, coordonnées) et gère son **opposition MSSanté**
  (vers Mon Espace Santé et entre professionnels) directement depuis la fiche.
  Détail : [E012-Changelogs.md](E012-Changelogs.md).
- **v1.14 (task-131)** — Synthèse IA d'un email : depuis le détail d'un message,
  le médecin déclenche l'affichage d'une synthèse rédigée par l'IA (mise en
  forme lisible, en-tête de contexte avec patient, praticien et date). Quand le
  service d'IA est indisponible, un message neutre l'indique sans bloquer la
  lecture. Détail : [E012-Changelogs.md](E012-Changelogs.md).
- **v1.13 (task-108)** — Vue Conversations : bascule Liste / Conversation ; en
  Conversation, les messages sont regroupés par fil (compteur « N messages »),
  dépliables pour voir les réponses. Détail : [E012-Changelogs.md](E012-Changelogs.md).
- **v1.12 (task-107)** — Notifications temps réel : le médecin est alerté in-app
  (toast) à l'arrivée d'un nouvel email ; s'il est sur le dossier concerné, le
  message apparaît directement en tête de liste. Push natives = suivi infra.
  Détail : [E012-Changelogs.md](E012-Changelogs.md).
- **v1.11 (task-106)** — Recherche d'emails : barre de recherche + filtres
  rapides (non lus, PJ, document médical, biologie) ; les résultats s'affichent
  dans la liste, l'effacement restaure la vue normale. Détail : [E012-Changelogs.md](E012-Changelogs.md).
- **v1.10 (task-105)** — Accusé de lecture : quand l'expéditeur en a fait la
  demande, le médecin peut émettre l'accusé depuis le détail, sur action
  explicite (jamais automatique). Détail : [E012-Changelogs.md](E012-Changelogs.md).
- **v1.9 (task-104)** — Mises à jour live : les emails au contenu non encore
  enrichi sont enrichis côté serveur puis la liste (et le détail ouvert) se
  mettent à jour automatiquement via un flux SSE folder-scoped, sans action
  utilisateur. Détail : [E012-Changelogs.md](E012-Changelogs.md).
- **v1.8 (task-103)** — Pagination inbox orientée scroll : la liste n'est plus
  bornée à 30 emails ; le scroll en bas charge progressivement les emails plus
  anciens (lots de 30, sans doublon, avec état fin-de-liste et retry sur erreur).
  Détail : [E012-Changelogs.md](E012-Changelogs.md).
- **v1.7 (task-102)** — Robustesse de session : sur token JWT expiré, le mobile
  rafraîchit la session puis rejoue la requête (un seul refresh pour des appels
  concurrents) ; si le refresh échoue, redirection `/login` avec message « session
  expirée ». Détail : [E012-Changelogs.md](E012-Changelogs.md).
- **v1.6 (task-101)** — HTML CDA responsive mobile : les tableaux larges ne
  débordent plus le viewport smartphone (scroll dans leur boîte), densité
  adaptée ≤480px, desktop inchangé. Côté `interop-cda` (feuille `cda_asip.xsl`).
  Détail : [E012-Changelogs.md](E012-Changelogs.md).
- **v1.5 (task-100)** — Compose / envoi : nouveau message, répondre, transférer ;
  champs To/Cc/Cci, objet, corps HTML (éditeur léger), pièces jointes, accusé
  de lecture ; envoi MSSanté avec threading. Détail : [E012-Changelogs.md](E012-Changelogs.md).
- **v1.4 (task-099)** — Actions de messagerie : marquer lu/non-lu, flag,
  supprimer (avec confirmation), déplacer vers un dossier — depuis la ligne
  (swipe) et le détail, avec mise à jour optimiste + rollback ; filtre statut
  Tous / Non lus / Flaggés. Détail : [E012-Changelogs.md](E012-Changelogs.md).
- **v1.3 (task-098)** — Biologie : tableau des résultats avec mise en évidence
  des valeurs hors norme (critiques/anormales) et filtre, workflow
  d'acquittement médecin (5 actions, confirmation, friction sur valeurs
  critiques), badge inbox + chip de filtre. Détail : [E012-Changelogs.md](E012-Changelogs.md).
- **v1.2 (task-097)** — Pièces jointes : liste fusionnée (MIME + documents
  médicaux), téléchargement par fichier et tout-en-ZIP, prévisualisation
  inline (image/PDF/texte). Détail : [E012-Changelogs.md](E012-Changelogs.md).
- **v1.1 (task-096)** — Consultation d'un email à parité : en-tête (titre
  document médical, identité patient, To/Cc, badges, version), corps HTML
  assaini + bascule texte brut + blocage des images distantes, documents
  médicaux structurés en onglets. Détail : [E012-Changelogs.md](E012-Changelogs.md).
- **v1.0 (task-095)** — Refonte du client mobile en structure miroir de
  `client-angular` ; sélection de répertoire et liste d'emails à parité de
  contenu (titre document médical, identité patient, badges PJ/document
  médical/biologie, tags, état lu/non-lu, flag). Détail technique :
  [E012-Changelogs.md](E012-Changelogs.md).
