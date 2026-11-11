# todo-task-465.md — Mesurer la charge de la boîte

**Repos**: api-mail
**Dependencies**: aucune
**Epic**: E024
**Priorité**: EPIC E024, demandée par l'humain le 2026-11-11. **À passer juste après task-453.** Règle d'or n° 5 :
mesurer avant d'améliorer. Les tasks 454 à 463 se jugent sur l'avant/après, pas sur une impression.

> **Origine.** Analyse du 2026-11-11, manque I1 (Sinsky et Shanafelt : « mesurer, réduire, déléguer » ; le temps passé
> hors des heures de travail prédit l'épuisement, selon Arndt 2017 et Akbar 2021). **Aucune source publique ne dit
> combien de documents un généraliste reçoit par jour** : nous le mesurerons nous-mêmes. Usage décidé par le PO le
> 2026-11-11, sur le modèle de task-452 : **mesure anonyme réservée à l'équipe produit**, rien n'est montré au médecin.
> Seule `api-mail` est touchée : aucun écran client.

## Ce qui est établi

- Le journal d'audit (`audit_traces`, base commune, partitionné, index `ix_audit_traces_mailbox_timestamp`) porte pour
  chaque acte : la boîte, la personne et son rôle, le type d'action et l'horodatage. Il comprend la lecture, l'envoi,
  la réponse, l'acquittement, le rattachement, le déplacement et la suppression.
- La catégorie des documents est en base de boîte (`MailMedicalDocument.Category`).
- `AuditTraceFilterDto` filtre déjà par personne, type et dates. Aucune agrégation n'existe.
- Le modèle d'exposition anonyme et le tableau de bord sont posés par task-452 : compteurs et durées, Grafana du
  projet.

## Objective

L'équipe produit suit, chaque jour, **la charge réelle** de la messagerie, sans connaître ni les boîtes, ni les
personnes, ni les patients.

Indicateurs, agrégés par jour sur l'ensemble des boîtes :
- **Volume reçu** par boîte et par jour (médiane, p90), réparti par catégorie de document : biologie, comptes rendus,
  sans document, patient.
- **Délai de prise de connaissance** : de la réception à la première lecture (p50, p95), et pour la biologie anormale
  de la réception à l'acquittement.
- **Part du travail délégué** : part des gestes faits par un délégataire ou un membre plutôt que par le titulaire.
- **Travail hors heures** : part des gestes faits avant 8 h, après 20 h, ou le week-end (Europe/Paris).
- **Temps de session** passé dans la messagerie par personne et par jour (médiane, p90), estimé depuis les gestes.

Règles :
- **Anonyme** :
  - aucun identifiant de boîte, de personne ou de patient dans les mesures exposées ;
  - un découpage n'est publié que s'il porte sur **au moins 5 boîtes** ;
  - le rôle n'est publié qu'en trois catégories : titulaire, délégataire, membre.
- **Calcul en tâche de fond**, une fois par jour, sous verrou distribué. Le calcul ne gêne jamais le médecin.
- **Indicateurs prévus pour la suite** :
  - « délai jusqu'au traitement » et « part traitée par le secrétariat » arriveront avec task-454 ;
  - « répartition par nature » arrivera avec task-456.

  Ces deux tasks déclarent chacune l'ajout de leur indicateur. Ici, ils sont seulement réservés sur le tableau de bord
  (« disponible après task-454 / task-456 »).
- **Mesure de référence** relevée **avant** la mise en service de task-454, et consignée.

## Definition of Done

- [ ] Agrégation quotidienne depuis `audit_traces` et les bases de boîte, sous verrou distribué ; aucune donnée
      nominative dans le résultat.
- [ ] Seuil d'anonymat (au moins 5 boîtes) appliqué à chaque découpage, testé.
- [ ] Tests unitaires du calcul de chaque indicateur (≥ 1 test par indicateur), dont le fuseau Europe/Paris et le
      passage à l'heure d'hiver pour le « hors heures ».
- [ ] **Test d'intégration de bout en bout (règle 1b)** sur la route d'exposition des indicateurs :
      - un jeu de traces sur 6 boîtes rend les volumes et délais attendus ;
      - un découpage sur 4 boîtes n'est pas publié ;
      - aucun identifiant de boîte, de personne ou de patient dans la réponse ;
      - cas d'échec : une plage de dates invalide → 400 en `ProblemDetails`.
      Vu rouge par mutation.
- [ ] Tableau de bord ajouté au Grafana du projet (à côté de celui de task-452) ; capture dans le `## Develop log`.
- [ ] Mesure de référence relevée sur l'environnement de recette (corpus fictif) et consignée dans le task file.
- [ ] Aucune donnée de santé ni donnée personnelle dans les mesures et les logs (revue du schéma exposé consignée).
- [ ] Build et tests verts : `HealthPlatform.Api.Mail.sln`.

## Manual Test Plan

1. Lancer le backend (`cd Api/Mail/src/AppHost && dotnet run`) et le tableau de bord Grafana du projet.
2. Rejouer une journée de gestes sur six boîtes de recette (seed e2e ou banc), puis déclencher le calcul quotidien.
3. Ouvrir le tableau de bord « Charge de la messagerie » : volumes, délais, part déléguée, hors heures.
4. Vérifier qu'aucune boîte, personne ou patient n'apparaît nulle part, et qu'un filtre sur moins de 5 boîtes
   n'affiche rien.

## Conformité santé / Ségur / ANS

- **Couloir Ségur** : hors couloir — pilotage produit
- **Vague Ségur** : hors Ségur
- **Exigences DSR honorées** : non applicable
- **INS** : non applicable — aucune donnée patient dans les mesures
- **Authentification PS** : non applicable au calcul (tâche de fond) ; la consultation du tableau de bord est réservée
  à l'équipe produit
- **Habilitations** : équipe produit seulement ; aucun accès depuis les clients médecin
- **Interop CI-SIS** : non applicable
- **Tracé PGSSI-S** : calcul quotidien en acte système ; lecture du journal par le calcul tracée en technique
  (`TechnicalActions`)
- **Consentement patient** : non applicable
- **Référentiels métier** : aucun
- **Hébergement HDS** : le calcul tourne dans l'environnement HDS ; seuls des agrégats anonymes en sortent
- **AIPD / impact RGPD** : à mettre à jour — réutilisation du journal d'audit à des fins statistiques anonymes
  (finalité, seuil d'anonymat de 5 boîtes)
