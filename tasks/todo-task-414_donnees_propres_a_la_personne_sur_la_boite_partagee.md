# todo-task-414 — Données propres à la personne sur la boîte partagée

**Repos**: api-mail, client-mobile, client-angular
**Dependencies**: aucune
**Epic**: E020

> **Origine** : audit du périmètre « boîte déléguée » du 2026-10-30
> (`Docs/audits/2026-10-30-audit-boite-deleguee.md`). Constats m1, m2, m3, m4 et l'index de
> `UserSettings`.
>
> **Décisions humaines du 2026-10-30** :
> - l'historique de recherche appartient à la **personne** ;
> - les conversations de l'assistant IA appartiennent à la **boîte**.

## Objectif

Sur une boîte partagée, ce qui est propre à chacun reste à chacun : historique de recherche et
préférences de notification. Ce qui est partagé l'est sans que l'un écrase le travail de l'autre :
brouillons et conversations IA.

## Règles

1. **Historique de recherche** (m2) : il est indexé par **boîte et personne**
   (`AuthenticationSubject`). Un délégataire ne voit ni n'efface les recherches du titulaire.
   L'effacement de son propre historique est tracé.
2. **Préférences de notification** (m1) : chaque personne reçoit les alertes « nouveau message » et
   « biologie anormale » selon **ses** préférences. Les préférences de la personne qui a lancé la
   synchro ne s'appliquent plus aux autres. La diffusion temps réel est filtrée par abonné.
3. **Conversations IA à la boîte** (m3, décision humaine) : toute personne de la boîte les liste et
   les reprend. Chaque question est imputée à son auteur réel dans la trace, et l'écran nomme
   l'auteur de chaque question.
4. **Brouillons partagés sans écrasement** (m4). Un brouillon porte une **version** :
   - une mise à jour ou une suppression faite sur une version périmée, ou pendant l'envoi, est
     refusée (409 problem+json, code dédié). Le client recharge le brouillon et le dit à la personne ;
   - le chemin d'échec d'un envoi ne réécrit pas un brouillon modifié ou supprimé entre-temps.
5. **`UserSettings`** : un index unique sur la personne (`UserId`). L'écriture concurrente du premier
   enregistrement ne crée pas de doublon.

## Definition of Done

- [ ] Build passes (0 errors) sur `api-mail`, `client-mobile`, `client-angular` (code-only)
- [ ] Tests pass (0 failures) sur chaque repo
- [ ] Unit tests :
  - clé d'historique par personne ;
  - filtrage des notifications par abonné ;
  - contrôle de version des brouillons ;
  - chemin d'échec de l'envoi sans réécriture.
- [ ] Test d'intégration de bout en bout, **deux personnes sur la même boîte**, pour
      `GET /search/history` : le titulaire cherche, le délégataire lit un historique vide, puis
      l'efface. L'historique du titulaire est intact. Vu rouge (règle 1b).
- [ ] Test d'intégration de bout en bout : le titulaire a coupé les alertes, le délégataire les a
      gardées. Un nouveau message arrive pendant une synchro lancée par le titulaire : seul le flux
      du délégataire reçoit l'alerte. Vu rouge.
- [ ] Test d'intégration de bout en bout pour `PUT /mail/drafts/{id}` : deux personnes modifient le
      même brouillon. La seconde, sur une version périmée, reçoit 409 avec le code dédié. Une
      suppression pendant l'envoi est refusée. Vu rouge.
- [ ] Test d'intégration de bout en bout : la reprise d'une conversation IA par le délégataire est
      tracée à son nom
- [ ] Migration : index unique sur `UserSettings.UserId`. Audit de migration (règle 7c) consigné.
- [ ] Mobile et weda2 : le 409 du brouillon recharge la rédaction et affiche « Ce brouillon a été
      modifié par une autre personne ». Test de composant.
- [ ] Mobile et weda2 : l'auteur de chaque question d'une conversation IA est affiché. Test de
      composant.
- [ ] Scénario **E2E-DRAFT-005** v1 (mobile requis, angular requis) : deux personnes de la boîte
      ouvrent le même brouillon. La seconde voit le message de conflit, et rien n'est perdu.
      Implémenté dans chaque client.
- [ ] Aucune donnée de santé en clair dans les logs (les recherches de patients restent minimisées)

## Manual Test Plan

- Backend : `cd Api/Mail && dotnet run --project src/AppHost` (profil e2e). Mobile et weda2.
- Le titulaire fait trois recherches. Le délégataire ouvre la recherche. Attendu : un historique vide.
- Le titulaire coupe les alertes « nouveau message ». Envoyer un message à la boîte. Attendu : le
  délégataire reçoit l'alerte, le titulaire non.
- Le titulaire et le délégataire ouvrent le même brouillon. Le titulaire enregistre, puis le
  délégataire enregistre. Attendu : le message de conflit chez le délégataire, et le brouillon
  rechargé.
- Le délégataire reprend une conversation IA du titulaire. Attendu : sa question est affichée à son
  nom.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : médecine de ville
- **Vague Ségur** : hors Ségur
- **Exigences DSR honorées** : non applicable — partage de boîte (règle 14). RGPD : minimisation et
  cloisonnement des données personnelles du professionnel.
- **INS** : non applicable — les recherches restent minimisées (pas d'INS ni de NIR enregistrés)
- **Authentification PS** : PSC. La personne vient de son identité PSC (`sub`).
- **Habilitations** : historique et préférences à la personne ; brouillons et conversations IA à la
  boîte (règle 14, décision humaine)
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : effacement de l'historique, questions IA imputées à leur auteur, conflit de
  brouillon. Conservation 3 653 jours.
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : oui — Redis et PostgreSQL de la plateforme
- **AIPD / impact RGPD** : à mettre à jour — conversations IA partagées entre les personnes de la
  boîte (décision humaine)
