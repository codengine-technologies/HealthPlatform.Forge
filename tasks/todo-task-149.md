# todo-task-149.md — Dashboard mobile enrichi + intégration dans les onglets

**Repos**: client-mobile
**Dependencies**: —
**Epic**: E012

## Objective

Faire du dashboard mobile (`home.page`, task-113) un vrai **tableau de bord
clinique** à parité raisonnée avec `mss-dashboard` Angular, et l'**intégrer à
la coquille `ion-tabs`** (aujourd'hui `/home` est un simple écran d'atterrissage
post-login, hors barre d'onglets).

1. **Intégration tabs** : nouvel onglet **Accueil** en première position
   (Accueil / Messages / Patients / Paramètres) ; la redirection post-login
   cible `/tabs/home`.
2. **Widgets portés** (adaptation mobile en cartes empilées, pull-to-refresh) :
   - **Compteurs messagerie** : Aujourd'hui / Non lus / Total INBOX
     (`getFolderToday`, `getFolderNotSeenToday`, `getFolder`) + nuage des tags
     à non-lus
   - **Bio en attente d'acquittement** : compteur + ventilation par dernière
     action (`getBiologyAckPendingSummary`) → deep-link inbox pré-filtrée
     (route existante « Bio à acquitter »)
   - **Résultats anormaux** : patients à biologie anormale non lue
     (`getAbnormalUnread`) avec criticité colorisée
   - **Patients avec mails non lus** : 5 patients (extensible 20,
     `getPatientsWithUnreadMails`) → actions Voir patient / Filtrer inbox
   - **Résumé des non-lus du jour** : cartes synthèse IA (`getRecentUnread` +
     `getEmailSummary`), retirables d'un geste
3. **Dynamique** : les compteurs se rafraîchissent au retour sur l'onglet et
   sur évènements SSE existants (nouveaux mails / enrichissement) — pas de
   polling agressif mobile.

Widgets **exclus** (posture desktop) : état de connexion PSC détaillé,
pilotage manuel de la synchronisation IMAP. À noter en divergence assumée.

US **frontend-only** : tous les endpoints existent. Aucun changement backend ni DTO.

## Definition of Done

- [ ] Build passe (`npm ci && npm run build`) — 0 erreur
- [ ] Tests passent (`npm test -- --watch=false --browsers=ChromeHeadless`) — 0 échec
- [ ] Onglet **Accueil** ajouté en 1re position ; post-login → `/tabs/home` ; redirect `/home` conservé (compat)
- [ ] Compteurs messagerie + nuage de tags non-lus → tap = inbox filtrée
- [ ] Tuile bio-ack avec ventilation par action → deep-link inbox « Bio à acquitter »
- [ ] Widget résultats anormaux (criticité colorisée) → tap = ouvre le mail concerné
- [ ] Widget patients non lus (5→20) → Voir patient (onglet Patients) / Filtrer inbox
- [ ] Cartes résumé IA des non-lus du jour, retirables ; IA indisponible → carte dégradée sans crash
- [ ] Rafraîchissement au retour d'onglet + sur évènements SSE ; pull-to-refresh
- [ ] `MssApiService` : méthodes manquantes ajoutées + tests unitaires
- [ ] Tests de rendu par widget (données, vide, erreur)
- [ ] Libellés FR en dur ; `data-testid` par widget et action
- [ ] Aucune donnée patient (INS/NIR) dans les logs client ni dans une route

## Manual Test Plan

- `cd Client/Mobile && npm start` ; se connecter → arrivée sur l'onglet **Accueil**
- Vérifier les 3 compteurs vs le client web (mêmes valeurs)
- Taper la tuile bio-ack → inbox filtrée « Bio à acquitter »
- Taper un patient du widget non-lus → fiche patient ouverte
- Lire un mail non lu → revenir sur Accueil → compteurs décrémentés
- Recevoir un mail de test (SSE) → compteur « Aujourd'hui » à jour
- Retirer une carte résumé IA → elle disparaît de la liste

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors DSR nouvelle — parité web (dashboard E009, task-035)
- **Exigences DSR honorées** : non applicable
- **INS** : affichage d'identités patient issues du backend (widgets) ; INS jamais dans une route mobile ni dans les logs
- **Authentification PS** : session existante, inchangée
- **Habilitations** : inchangées
- **Interop CI-SIS** : non applicable — restitution de métadonnées déjà enrichies
- **Tracé PGSSI-S** : « Voir l'email » depuis un widget marque le mail lu via le canal tracé existant
- **Consentement patient** : non applicable
- **Référentiels métier** : codes de criticité HL7 (AA/HH/LL) restitués tels que fournis par le backend
- **Hébergement HDS** : oui — backend existant, pas de persistance locale
- **AIPD / impact RGPD** : inchangé
